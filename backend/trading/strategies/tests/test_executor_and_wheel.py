from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import Client, BrokerAccount, AccountSnapshot
from portfolio.models import Portfolio
from strategies.models import (
    StrategyDefinition,
    StrategyVersion,
    StrategyInstance,
    Recommendation,
)
from trading.strategies.base import StrategyContext
from trading.strategies.executor import (
    build_strategy_context,
    run_strategy_instance,
)
from trading.strategies.wheel_v1 import WheelStrategy


class StrategyExecutorAndWheelTests(TestCase):
    def setUp(self):
        # --- Core client / account / portfolio setup ---
        self.client_obj = Client.objects.create(
            name="Demo Client",
            is_active=True,
            settings={},
        )

        self.broker_account = BrokerAccount.objects.create(
            client=self.client_obj,
            kind=BrokerAccount.Kind.SIMULATED,
            account_code="U1234567",
            base_currency="USD",
            nickname="SIM",
            metadata={},
        )

        self.portfolio = Portfolio.objects.create(
            client=self.client_obj,
            name="Wheel v1 (Demo)",
            base_currency="USD",
            broker_account=self.broker_account,
            metadata={},
        )

        # Two snapshots to verify "latest snapshot wins"
        older_ts = timezone.now() - timezone.timedelta(days=1)
        newer_ts = timezone.now()

        self.older_snapshot = AccountSnapshot.objects.create(
            client=self.client_obj,
            broker_account=self.broker_account,
            asof_ts=older_ts,
            currency="USD",
            cash=Decimal("50000"),
            buying_power=Decimal("150000"),
            maintenance_margin=Decimal("20000"),
            used_margin=Decimal("5000"),
            extras={"marker": "older"},
        )

        self.newer_snapshot = AccountSnapshot.objects.create(
            client=self.client_obj,
            broker_account=self.broker_account,
            asof_ts=newer_ts,
            currency="USD",
            cash=Decimal("100000"),
            buying_power=Decimal("300000"),
            maintenance_margin=Decimal("50000"),
            used_margin=Decimal("10000"),
            extras={"marker": "newer"},
        )

        # --- Strategy definition / version / instance ---

        self.strategy_def = StrategyDefinition.objects.create(
            name="Wheel",
            slug="wheel",
            description="Wheel strategy v1",
        )

        # Use the real WheelStrategy implementation via code_ref
        self.strategy_version = StrategyVersion.objects.create(
            strategy_def=self.strategy_def,
            version="v1",
            # IMPORTANT: module path + class name
            code_ref="trading.strategies.wheel_v1:WheelStrategy",
            schema={},  # for this test we don't need a strict schema
        )

        # Minimal-but-valid config for WheelStrategy
        self.strategy_instance = StrategyInstance.objects.create(
            client=self.client_obj,
            name="Wheel v1 (Demo)",
            strategy_version=self.strategy_version,
            portfolio=self.portfolio,
            enabled=True,
            tags="test",
            config={
                "underlying_universe": ["AAPL", "MSFT"],
                "min_dte": 20,
                "max_dte": 40,
                "target_delta": -0.3,
                "max_positions": 3,
            },
        )

    # ------------------------------------------------------------------ #
    # Context builder tests
    # ------------------------------------------------------------------ #

    def test_build_strategy_context_uses_latest_snapshot(self):
        """
        build_strategy_context should pick the latest AccountSnapshot for the
        portfolio's broker_account and surface its values in the context.
        """
        ctx: StrategyContext = build_strategy_context(self.strategy_instance)

        # Latest snapshot values should be reflected
        self.assertEqual(ctx.cash, self.newer_snapshot.cash)
        self.assertEqual(ctx.buying_power, self.newer_snapshot.buying_power)
        self.assertEqual(ctx.maintenance_margin, self.newer_snapshot.maintenance_margin)
        self.assertEqual(ctx.used_margin, self.newer_snapshot.used_margin)

        # Sanity checks on structural fields
        self.assertEqual(ctx.client, self.client_obj)
        self.assertEqual(ctx.portfolio, self.portfolio)
        self.assertEqual(ctx.broker_account, self.broker_account)
        self.assertIsInstance(ctx.asof_ts, type(timezone.now()))

    # ------------------------------------------------------------------ #
    # WheelStrategy runtime tests (via executor)
    # ------------------------------------------------------------------ #

    def test_run_strategy_instance_returns_diagnostic_action(self):
        """
        run_strategy_instance should resolve WheelStrategy via the registry,
        build a context, and return at least one PlannedAction from WheelStrategy.
        """
        actions = run_strategy_instance(
            instance=self.strategy_instance,
            asof_ts=None,
            persist_recommendations=False,
        )

        # We expect our stub WheelStrategy to return exactly one diagnostic action
        self.assertEqual(len(actions), 1)
        act = actions[0]

        self.assertEqual(act.action, "diagnostic")
        self.assertEqual(act.rationale, "WheelStrategy v1 diagnostic only (no live trades).")
        self.assertIsNone(act.underlier)
        self.assertEqual(act.params.get("strategy"), "wheel")
        self.assertEqual(act.params.get("instance"), "Wheel v1 (Demo)")

        summary = act.params.get("summary") or {}
        # Summary should include the universe and account numbers as strings
        self.assertEqual(summary.get("universe"), ["AAPL", "MSFT"])
        self.assertEqual(summary.get("cash"), str(self.newer_snapshot.cash))
        self.assertEqual(summary.get("buying_power"), str(self.newer_snapshot.buying_power))
        self.assertEqual(summary.get("num_positions"), 0)
        self.assertEqual(summary.get("num_open_orders"), 0)

    def test_run_strategy_instance_can_persist_recommendations(self):
        """
        When persist_recommendations=True, run_strategy_instance should turn
        PlannedActions into Recommendation rows linked to the instance.
        """
        self.assertEqual(Recommendation.objects.count(), 0)

        actions = run_strategy_instance(
            instance=self.strategy_instance,
            asof_ts=None,
            persist_recommendations=True,
        )

        self.assertEqual(len(actions), 1)

        recs = Recommendation.objects.filter(strategy_instance=self.strategy_instance)
        self.assertEqual(recs.count(), 1)

        rec = recs.first()
        # Recommendation fields should reflect the PlannedAction + instance/version
        self.assertEqual(rec.action, "diagnostic")
        self.assertEqual(rec.strategy_instance, self.strategy_instance)
        self.assertEqual(rec.strategy_version, self.strategy_version)
        self.assertEqual(rec.portfolio, self.portfolio)
        self.assertEqual(rec.broker_account, self.broker_account)
        self.assertEqual(rec.client, self.client_obj)
        self.assertIsNotNone(rec.asof_ts)
        self.assertIsInstance(rec.params, dict)
        self.assertIn("summary", rec.params)
