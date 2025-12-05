from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import Client, BrokerAccount
from portfolio.models import Portfolio, Instrument, Position
from strategies.models import StrategyDefinition, StrategyVersion, StrategyInstance
from trading.strategies.base import StrategyContext, PlannedAction
from trading.strategies.wheel_v1 import WheelStrategy  # adjust path if needed
from strategies.models import Signal, Opportunity, Recommendation


class WheelStrategySkeletonTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            name="Wheel Test Client",
            is_active=True,
            settings={},
        )

        self.broker_account = BrokerAccount.objects.create(
            client=self.client_obj,
            kind=BrokerAccount.Kind.SIMULATED,
            account_code="U555555",
            base_currency="USD",
            nickname="SIM",
            metadata={},
        )

        self.portfolio = Portfolio.objects.create(
            client=self.client_obj,
            name="Wheel Test Portfolio",
            base_currency="USD",
            broker_account=self.broker_account,
            metadata={},
        )

        self.instrument = Instrument.objects.create(
            symbol="BABA",
            name="Alibaba Group Holding Ltd",
            exchange="NYSE",
            asset_type=Instrument.AssetType.EQUITY,
            currency="USD",
            is_active=True,
        )

        self.strategy_def = StrategyDefinition.objects.create(
            name="Wheel",
            slug="wheel",
            description="Wheel strategy v1",
        )

        self.strategy_version = StrategyVersion.objects.create(
            strategy_def=self.strategy_def,
            version="v1",
            code_ref="trading.strategies.wheel_v1:WheelStrategy",
            schema={},
        )

        self.instance = StrategyInstance.objects.create(
            client=self.client_obj,
            name="Wheel v1 (Test)",
            strategy_version=self.strategy_version,
            portfolio=self.portfolio,
            enabled=True,
            tags="test",
            config={
                # example minimal config; adjust to match your current WheelStrategy
                "underliers": ["BABA"],
                "put_delta_target": -0.25,
                "put_days_out": 30,
                "max_positions_per_underlier": 1,
                "max_capital_per_underlier": 50000,
            },
        )

    def _make_context(
        self,
        cash: Decimal,
        buying_power: Decimal,
        with_stock: bool = False,
    ) -> StrategyContext:
        """
        Build a minimal StrategyContext for WheelStrategy skeleton tests.
        """
        positions = []
        if with_stock:
            Position.objects.create(
                client=self.client_obj,
                portfolio=self.portfolio,
                broker_account=self.broker_account,
                instrument=self.instrument,
                ibkr_con=None,
                qty=Decimal("100"),
                avg_cost=Decimal("70"),
                market_price=Decimal("80"),
                market_value=Decimal("8000"),
                asof_ts=timezone.now(),
            )
            positions = list(self.portfolio.positions.all())

        ctx = StrategyContext(
            client=self.client_obj,
            portfolio=self.portfolio,
            broker_account=self.broker_account,
            asof_ts=timezone.now(),
            cash=cash,
            buying_power=buying_power,
            maintenance_margin=Decimal("0"),
            used_margin=Decimal("0"),
            positions=positions,
            open_orders=[],
            recent_executions=[],
            config={},
            extras={},
        )
        return ctx

    def test_wheel_with_simple_account_state(self):
        """
        T0061.1 — WheelStrategy should produce either zero or some sensible
        PlannedActions given a simple account/position state.
        This is intentionally light-weight: we don't assert the exact trade,
        only that output is well-formed.
        """
        strategy = WheelStrategy(self.instance)
        ctx = self._make_context(
            cash=Decimal("100000"),
            buying_power=Decimal("300000"),
            with_stock=False,
        )

        actions = strategy.run(ctx)
        # Skeleton might still return [], so we only check types.
        for act in actions:
            self.assertIsInstance(act, PlannedAction)
            self.assertIsInstance(act.confidence, Decimal)
            self.assertIsInstance(act.params, dict)

    def test_wheel_risk_conditions_can_block_recommendations(self):
        """
        T0061.2 — If config sets very strict limits (e.g., no buying power),
        WheelStrategy should not emit actionable recommendations.
        """
        strict_instance = self.instance
        strict_instance.config = {
            "underliers": ["BABA"],
            "put_delta_target": -0.25,
            "put_days_out": 30,
            "max_positions_per_underlier": 0,      # block new positions
            "max_capital_per_underlier": 0,        # block capital
        }
        strict_instance.save(update_fields=["config"])

        strategy = WheelStrategy(strict_instance)
        ctx = self._make_context(
            cash=Decimal("0"),
            buying_power=Decimal("0"),
            with_stock=False,
        )

        actions = strategy.run(ctx)
        # We expect no new trade actions when everything is blocked.
        self.assertEqual(len(actions), 0)

    def test_wheel_outputs_can_map_to_signal_opp_rec(self):
        """
        T0061.3 — Ensure Wheel outputs *could* be mapped cleanly to
        Signal/Opportunity/Recommendation. We don't persist in this test;
        we only assert that fields are compatible with our recording helpers.
        """
        strategy = WheelStrategy(self.instance)
        ctx = self._make_context(
            cash=Decimal("100000"),
            buying_power=Decimal("300000"),
            with_stock=False,
        )

        actions = strategy.run(ctx)
        for act in actions:
            # these fields must exist for our recording helpers
            self.assertTrue(hasattr(act, "underlier"))
            self.assertTrue(hasattr(act, "ibkr_con"))
            self.assertTrue(hasattr(act, "action"))
            self.assertTrue(hasattr(act, "params"))
            self.assertTrue(hasattr(act, "confidence"))
            self.assertTrue(hasattr(act, "rationale"))
