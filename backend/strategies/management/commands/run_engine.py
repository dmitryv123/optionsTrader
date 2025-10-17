from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime
from decimal import Decimal
import uuid

from accounts.models import AccountSnapshot
from portfolio.models import Position
from strategies.models import (
    StrategyInstance, StrategyRun, Signal, Opportunity, Recommendation
)

# The command is advice-only: it writes Recommendation rows, nothing else.
# It’s conservative: it requires a profit-capture signal (≥ threshold) to trigger a close+roll plan.
# That means if you don’t have Signal(type="profit_capture_status") for a position, it skips it (safe default).
# It selects the best Opportunity for the day (by metrics.ror_pct) and uses that to form the new sell_put ticket.
# Quantities default to the current short-put absolute quantity.
# If you pass --dry-run, it computes but does not write recommendations.

D = lambda x: Decimal(str(x))


def latest_snapshot(ba_id):
    return (AccountSnapshot.objects
            .filter(broker_account_id=ba_id)
            .order_by('-asof_ts')
            .first())


def current_positions_map(portfolio_id):
    """
    Return latest position per ibkr_con (or instrument if no contract).
    Note: we store snapshots append-only; to get 'current' we pick the latest row per key.
    """
    latest = {}
    qs = (Position.objects
          .filter(portfolio_id=portfolio_id)
          .order_by('-asof_ts'))
    for p in qs:
        key = p.ibkr_con_id or f"inst:{p.instrument_id}"
        if key not in latest:
            latest[key] = p
    return latest


def is_short_put(pos):
    ic = pos.ibkr_con
    return (
            ic is not None
            and (ic.sec_type or "").upper() == "OPT"
            and (ic.right or "").upper() == "P"
            and pos.qty < 0
    )


def find_signal_profit_70(inst, portfolio_id, underlier_id, asof_date):
    """
    Optional: we look for a signal like 'profit_capture_status' with >=70%.
    If absent, we return None and the engine can choose to skip or continue.
    """
    s = (Signal.objects
         .filter(strategy_instance=inst,
                 portfolio_id=portfolio_id,
                 underlier_id=underlier_id,
                 type="profit_capture_status",
                 asof_ts__date=asof_date)
         .order_by('-asof_ts')
         .first())
    if not s:
        return None
    pct = s.payload.get('profit_captured_pct')
    try:
        return float(pct)
    except Exception:
        return None


def choose_opportunity(client_id, asof_date, underlier_id=None):
    """
    Pick today's best opportunity (option-agnostic).
    If underlier_id is provided, prefer that; else take best by ror_pct.
    """
    qs = Opportunity.objects.filter(client_id=client_id, asof_ts__date=asof_date)
    if underlier_id:
        qs = qs.filter(underlier_id=underlier_id)
    # order by metrics.ror_pct desc when present
    opps = list(qs)
    if not opps:
        return None

    def ror(o):
        try:
            return float(o.metrics.get('ror_pct', 0))
        except Exception:
            return 0.0

    opps.sort(key=ror, reverse=True)
    return opps[0]


class Command(BaseCommand):
    help = "Advice-only strategy runner: emits Recommendations (e.g., close+sell_put) per enabled StrategyInstance."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="YYYY-MM-DD (defaults to today UTC)")
        parser.add_argument("--only", help="Run only this StrategyInstance id (UUID)", default=None)
        parser.add_argument("--dry-run", action="store_true", help="Compute advice but do not write Recommendations")

    def handle(self, *args, **opts):
        asof = timezone.now()
        if opts["date"]:
            asof = timezone.make_aware(datetime.fromisoformat(opts["date"]))

        inst_qs = StrategyInstance.objects.select_related("strategy_version", "portfolio", "client").filter(
            enabled=True)
        if opts["only"]:
            inst_qs = inst_qs.filter(id=opts["only"])

        ran = 0
        for inst in inst_qs:
            portfolio = inst.portfolio
            if not portfolio:
                continue
            ba = portfolio.broker_account
            snap = latest_snapshot(ba.id) if ba else None
            run = StrategyRun.objects.create(strategy_instance=inst, run_ts=asof, mode="daily", status="ok", stats={})
            self.stdout.write(
                self.style.NOTICE(f"[ADVICE] {inst.name} on {portfolio.name} (client={inst.client.name})"))

            # Config knobs (with safe defaults)
            cfg = inst.config or {}
            min_profit_capture = float(cfg.get("min_profit_capture_pct", 70))
            min_candidate_ror = float(cfg.get("min_premium_yield_pct", 0.5))  # in percent terms (e.g., 0.5 = 0.5%)
            incremental_bps = float(cfg.get("min_incremental_ror_bps", 30))  # 30 bps = 0.30%
            target_delta = float(cfg.get("put_delta_target", -0.25))
            dte_list = cfg.get("put_days_out", [7, 14])
            underlier_whitelist = set(cfg.get("underliers", []))

            # Build a 'current positions' view
            cur = current_positions_map(portfolio.id)
            short_puts = [p for p in cur.values() if is_short_put(p)]

            # Strategy: for each short put, if there is a >=70% profit signal AND a better ROR opp, propose close+sell_put
            emitted = 0
            for sp in short_puts:
                underlier_id = sp.instrument_id  # we store underlier as instrument on pos
                # If whitelist exists and this underlier not in it, skip
                if underlier_whitelist and sp.instrument.symbol not in underlier_whitelist:
                    continue

                pct = find_signal_profit_70(inst, portfolio.id, underlier_id, asof.date())
                if pct is None or pct < min_profit_capture:
                    # No strong profit-capture evidence today—skip to be conservative
                    continue

                opp = choose_opportunity(inst.client_id, asof.date(), underlier_id=None)  # pick best available opp
                if not opp:
                    continue

                try:
                    opp_ror = float(opp.metrics.get("ror_pct", 0))
                except Exception:
                    opp_ror = 0.0

                if opp_ror < min_candidate_ror:
                    continue

                # (Optional) simple incremental check if you have an estimate for current position's remaining yield
                # For minimal MVP, we just require candidate ROR >= min_candidate_ror

                plan_id = uuid.uuid4()
                close_params = {
                    "reason": "take_profit_and_fund_better_opportunity",
                    "position_ref": str(sp.ibkr_con_id or sp.instrument_id),
                    "qty": int(abs(sp.qty) or 1),
                    "opportunity_id": str(opp.id),
                }

                # New put: use opp metrics as a hint; if missing, fall back to config
                sell_put_params = {
                    "symbol": opp.underlier.symbol,
                    "target_delta": target_delta,
                    "dte": dte_list[0] if isinstance(dte_list, (list, tuple)) and dte_list else 7,
                    "strike": opp.metrics.get("strike", None),
                    "limit_price": opp.metrics.get("premium", None),
                    "est_ror_pct": opp_ror,
                    "qty": int(abs(sp.qty) or 1),
                    "opportunity_id": str(opp.id),
                }

                if not opts["dry_run"]:
                    # close current
                    Recommendation.objects.create(
                        client_id=inst.client_id,
                        portfolio_id=portfolio.id,
                        broker_account_id=ba.id,
                        strategy_instance=inst,
                        strategy_version=inst.strategy_version,
                        asof_ts=asof,
                        underlier_id=sp.instrument_id,
                        ibkr_con_id=sp.ibkr_con_id,
                        action="close",
                        params=close_params,
                        confidence=D("85.0"),
                        rationale=f"Captured ~{int(pct)}%; redeploy to better ROR.",
                        plan_id=plan_id,
                        opportunity=opp,
                    )
                    # open new
                    Recommendation.objects.create(
                        client_id=inst.client_id,
                        portfolio_id=portfolio.id,
                        broker_account_id=ba.id,
                        strategy_instance=inst,
                        strategy_version=inst.strategy_version,
                        asof_ts=asof,
                        underlier_id=opp.underlier_id,
                        ibkr_con=None,
                        action="sell_put",
                        params=sell_put_params,
                        confidence=D("80.0"),
                        rationale="Candidate meets min yield; re-deploy freed margin.",
                        plan_id=plan_id,
                        opportunity=opp,
                    )
                emitted += 2

            # If no short puts qualified, you could optionally consider pure “sell_put” from best opportunity when cash allows.
            # Minimal MVP keeps it conservative (no action when signals missing).
            run.stats = {"emitted": emitted, "short_puts_seen": len(short_puts)}
            run.save(update_fields=["stats"])
            ran += 1

        self.stdout.write(self.style.SUCCESS(f"✅ run_engine finished: instances={ran}"))
