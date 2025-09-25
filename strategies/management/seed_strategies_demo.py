from django.core.management.base import BaseCommand
from django.utils import timezone
from decimal import Decimal

from accounts.models import Client
from portfolio.models import Portfolio, Instrument, IbkrContract
from strategies.models import (
    StrategyDefinition,
    StrategyVersion,
    StrategyInstance,
    StrategyRun,
    Signal,
    Opportunity,
    Recommendation,
)


class Command(BaseCommand):
    help = "Seed strategy catalogue (wheel@v1), an instance, an Opportunity, and paired demo recommendations"

    def handle(self, *args, **options):
        # Resolve demo tenant/portfolio/instrument (created by accounts.seed_demo)
        client = Client.objects.get(name="Demo Client")
        portfolio = Portfolio.objects.get(client=client, name="Main Portfolio")
        underlier = Instrument.objects.get(symbol="AAPL", asset_type="equity")
        ibkr_con = IbkrContract.objects.filter(instrument=underlier).first()

        # 1) Strategy catalogue: Wheel@v1
        wheel_def, _ = StrategyDefinition.objects.get_or_create(
            slug="wheel",
            defaults={"name": "Wheel", "description": "Cash-secured puts / covered calls"},
        )

        schema = {
            "type": "object",
            "properties": {
                "underliers": {"type": "array", "items": {"type": "string"}},
                "cash_utilization_pct": {"type": "number", "minimum": 0, "maximum": 1},
                "put_days_out": {"type": "array", "items": {"type": "integer"}},
                "put_delta_target": {"type": "number"},
                "min_premium_yield_pct": {"type": "number"},
                "roll_when": {"type": "object"},
                "covered_calls": {"type": "object"},
                "position_limits": {"type": "object"},
            },
            "required": ["underliers", "put_days_out", "put_delta_target"],
            "additionalProperties": True,
        }

        wheel_v1, _ = StrategyVersion.objects.get_or_create(
            strategy_def=wheel_def,
            version="v1",
            defaults={"schema": schema, "code_ref": "engine.plugins.wheel.v1"},
        )

        # 2) Tenant-bound StrategyInstance
        config = {
            "underliers": ["AAPL"],
            "cash_utilization_pct": 0.6,
            "put_days_out": [7, 14],
            "put_delta_target": -0.25,
            "min_premium_yield_pct": 0.6,
            "roll_when": {"days_to_expiry_lte": 3, "remaining_premium_pct_lte": 20},
            "covered_calls": {"target_delta": 0.20, "itm_roll_threshold_pct": 10},
            "position_limits": {"per_underlier_contracts_max": 10, "per_underlier_notional_max": 50000},
        }

        instance, _ = StrategyInstance.objects.get_or_create(
            client=client,
            name="Wheel v1 (Demo)",
            defaults={"strategy_version": wheel_v1, "portfolio": portfolio, "enabled": True, "config": config},
        )

        # 3) Record a demo run
        run = StrategyRun.objects.create(
            strategy_instance=instance,
            run_ts=timezone.now(),
            mode=StrategyRun.Mode.DAILY,
            status="ok",
            stats={"note": "demo run"},
        )

        # 4) Demo Signal (profit capture status)
        Signal.objects.get_or_create(
            client=client,
            strategy_instance=instance,
            asof_ts=run.run_ts,
            portfolio=portfolio,
            underlier=underlier,
            ibkr_con=ibkr_con,
            type="profit_capture_status",
            defaults={"payload": {"profit_captured_pct": 70, "dte": 30, "remaining_premium_pct": 30}},
        )

        # 5) Demo Opportunity (candidate with metrics)
        opp = Opportunity.objects.create(
            client=client,
            asof_ts=run.run_ts,
            underlier=underlier,
            ibkr_con=None,
            metrics={"ror_pct": 1.2, "iv_rank": 34, "risk": 0.55, "delta": -0.25, "dte": 14},
            required_margin=Decimal("15000"),
            notes="Demo candidate: meets min yield and delta",
        )

        # Paired Recommendations (plan: close old, open new)
        import uuid as _uuid
        plan_id = _uuid.uuid4()

        Recommendation.objects.get_or_create(
            client=client,
            portfolio=portfolio,
            strategy_instance=instance,
            strategy_version=wheel_v1,
            asof_ts=run.run_ts,
            underlier=underlier,
            ibkr_con=ibkr_con,
            action="close",
            params={
                "reason": "take_profit_and_fund_better_opportunity",
                "position_ref": "DEMO-POS-UUID",
                "opportunity_id": str(opp.id),
            },
            defaults={
                "confidence": Decimal("85.0"),
                "rationale": "Captured ~70%; better ROR candidate available.",
                "plan_id": plan_id,
                "opportunity": opp,
            },
        )

        Recommendation.objects.get_or_create(
            client=client,
            portfolio=portfolio,
            strategy_instance=instance,
            strategy_version=wheel_v1,
            asof_ts=run.run_ts,
            underlier=underlier,
            ibkr_con=None,
            action="sell_put",
            params={
                "symbol": "AAPL",
                "target_delta": -0.25,
                "dte": 14,
                "strike": 180,
                "limit_price": 2.50,
                "est_ror_pct": 1.2,
                "opportunity_id": str(opp.id),
            },
            defaults={
                "confidence": Decimal("80.0"),
                "rationale": "Candidate meets min yield and delta; re-deploy freed margin.",
                "plan_id": plan_id,
                "opportunity": opp,
            },
        )

        self.stdout.write(self.style.SUCCESS(
            "✅ Seeded wheel@v1 catalogue, instance, run, signal, opportunity, and paired recommendations"
        ))

