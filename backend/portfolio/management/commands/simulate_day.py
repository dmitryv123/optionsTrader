from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal
from datetime import datetime
import uuid

from accounts.models import BrokerAccount, AccountSnapshot, Client
from portfolio.models import Portfolio, Instrument, IbkrContract, Position, Order, Execution
from strategies.models import Recommendation, Opportunity, StrategyInstance

# --- helpers ---
D = lambda x: Decimal(str(x))


def fee_for(broker_acct: BrokerAccount, *, is_option: bool, qty: Decimal) -> Decimal:
    meta = broker_acct.metadata or {}
    if is_option:
        per_ct = D(meta.get("fee_option_per_contract", "0.65"))
        return per_ct * qty.copy_abs()
    else:
        per_share = D(meta.get("fee_equity_per_share", "0.005"))
        return per_share * qty.copy_abs()


def est_fill_price(underlier: Instrument, action: str, params: dict) -> Decimal:
    """
    v1: use limit_price if provided; else assume a conservative last price from params
    You can wire real quotes later; for now, accept provided limit/estimates.
    """
    lp = params.get("limit_price")
    if lp is not None:
        return D(lp)
    # fallback
    return D(params.get("est_fill_price", "0"))


def notional_per_contract(params: dict) -> Decimal:
    # options multiplier default 100
    mult = D(params.get("multiplier", 100))
    strike = D(params.get("strike", 0))
    return strike * mult


def reserve_margin(broker_acct: BrokerAccount, action: str, params: dict) -> Decimal:
    # cash-secured put reserve (simplified)
    if action == "sell_put":
        return notional_per_contract(params) * D(params.get("qty", 0)).copy_abs()
    return D("0")


# --- core simulate ---
class Command(BaseCommand):
    help = "Simulate daily execution for SIM broker accounts from Recommendations (advice-only to filled trades)."

    def add_arguments(self, parser):
        parser.add_argument("--date", help="YYYY-MM-DD as-of date (default: today UTC)")
        parser.add_argument("--client", help="Filter to a specific client name", default=None)
        parser.add_argument("--portfolio", help="Filter to a specific portfolio name", default=None)
        parser.add_argument("--execute", action="store_true",
                            help="Actually create Orders/Executions/Positions (otherwise dry-run)")
        parser.add_argument("--plan-id", help="Only execute recommendations for a specific plan UUID", default=None)

    def handle(self, *args, **opts):
        as_of = timezone.now()
        if opts["date"]:
            as_of = timezone.make_aware(datetime.fromisoformat(opts["date"]))

        # 1) pick SIM broker accounts
        bas = BrokerAccount.objects.filter(kind="SIM")
        if opts["client"]:
            bas = bas.filter(client__name=opts["client"])

        if not bas.exists():
            self.stdout.write(self.style.WARNING("No SIM broker accounts found. Create one in Admin (kind=SIM)."))
            return

        # 2) collect today’s recs for their portfolios
        recs = Recommendation.objects.select_related(
            "client", "portfolio", "broker_account", "underlier", "strategy_instance", "strategy_version", "opportunity"
        ).filter(
            broker_account__in=bas, asof_ts__date=as_of.date()
        ).order_by("asof_ts", "plan_id", "action")

        if opts["portfolio"]:
            recs = recs.filter(portfolio__name=opts["portfolio"])
        if opts["plan_id"]:
            recs = recs.filter(plan_id=opts["plan_id"])

        if not recs.exists():
            self.stdout.write(self.style.WARNING("No recommendations for SIM accounts on this date."))
            return

        self.stdout.write(self.style.NOTICE(f"Simulating {recs.count()} recommendations @ {as_of.date()}"))

        # 3) per account working state (cash/margin). Use latest snapshot as start
        state = {}
        for ba in bas:
            snap = AccountSnapshot.objects.filter(broker_account=ba).order_by("-asof_ts").first()
            cash = D(snap.cash if snap else 0)
            used_margin = D(snap.used_margin if snap else 0)
            state[ba.id] = {"cash": cash, "used_margin": used_margin}

        created_orders = 0
        created_execs = 0
        created_positions = 0

        # 4) execute recs (very simplified v1)
        for r in recs:
            ba = r.broker_account
            st = state[ba.id]
            params = r.params or {}
            qty = D(params.get("qty", 0))
            if qty == 0:
                continue

            # basic accounting
            is_option = (r.ibkr_con and r.ibkr_con.sec_type.upper() == "OPT") or params.get("type") == "option"
            fill_price = est_fill_price(r.underlier, r.action, params)
            fee = fee_for(ba, is_option=is_option, qty=qty.copy_abs())

            # cash deltas per action (Wheel-centric v1)
            cash_delta = D("0")
            position_delta = D("0")  # shares for equity, contracts for option short
            if r.action == "sell_put":
                premium = fill_price * qty  # positive qty for short 1? We'll assume qty is positive here = contracts
                cash_delta += premium
                # reserve margin
                st["used_margin"] += reserve_margin(ba, r.action, params)
            elif r.action == "sell_call":
                premium = fill_price * qty
                cash_delta += premium
            elif r.action == "close":
                # assume closing a short option position: pay to buy back
                cash_delta -= (fill_price * qty.copy_abs())
            elif r.action == "open_long":
                cash_delta -= (fill_price * qty)
                position_delta += qty
            elif r.action == "close_long":
                cash_delta += (fill_price * qty.copy_abs())
                position_delta -= qty.copy_abs()
            # fees
            cash_delta -= fee

            # check cash; if negative beyond tolerance, skip in dry-run mode
            if not opts["execute"]:
                self.stdout.write(self.style.HTTP_INFO(
                    f"DRY-RUN {r.action} {r.underlier.symbol} qty={qty} px={fill_price} fee={fee} cashΔ={cash_delta}"
                ))
                continue

            # 4.1 create Order
            ord_obj = Order.objects.create(
                client=r.client, broker_account=ba, ibkr_con=r.ibkr_con,
                ibkr_order_id=uuid.uuid4().int >> 96,  # synthetic order id
                parent_ibkr_order_id=None,
                side="SELL" if r.action in ("sell_put", "sell_call", "close") else "BUY",
                order_type="LMT" if "limit_price" in params else "MKT",
                limit_price=fill_price if "limit_price" in params else None,
                aux_price=None, tif="DAY", status="Filled",
                raw={"source": "SIM", "rec_id": str(r.id)},
                created_ts=as_of, updated_ts=as_of,
            );
            created_orders += 1

            # 4.2 create Execution
            exec_obj = Execution.objects.create(
                client=r.client, order=ord_obj, ibkr_exec_id=str(uuid.uuid4()),
                fill_ts=as_of, qty=qty, price=fill_price, fee=fee, venue="SIM",
                raw={"note": "simulated fill"}
            );
            created_execs += 1

            # 4.3 adjust cash & positions
            st["cash"] += cash_delta

            # position snapshot row (append-only) — you can also reconcile aggregate separately
            Position.objects.create(
                client=r.client, portfolio=r.portfolio, broker_account=ba,
                instrument=r.underlier, ibkr_con=r.ibkr_con,
                qty=qty if r.action.startswith("open") else D("0"),  # v1: record event rows; you can aggregate later
                avg_cost=fill_price if r.action.startswith("open") else D("0"),
                market_price=fill_price, market_value=fill_price * qty,
                asof_ts=as_of,
            );
            created_positions += 1

        # 5) write a closing AccountSnapshot per SIM account
        for ba in bas:
            st = state[ba.id]
            AccountSnapshot.objects.create(
                client=ba.client, broker_account=ba, asof_ts=as_of,
                currency=ba.base_currency,
                cash=st["cash"], buying_power=st["cash"] * D("4"),  # trivial placeholder
                maintenance_margin=st["used_margin"], used_margin=st["used_margin"],
                extras={"sim": True}
            )

        self.stdout.write(self.style.SUCCESS(
            f"✅ simulate_day complete: orders={created_orders}, execs={created_execs}, pos_rows={created_positions}"
        ))
