from __future__ import annotations

from decimal import Decimal
import uuid

from django.test import TestCase
from django.utils import timezone

from accounts.models import Client, BrokerAccount
from portfolio.models import Portfolio, Instrument, IbkrContract
from strategies.models import (
    StrategyDefinition,
    StrategyVersion,
    StrategyInstance,
    Recommendation,
)
from trading.strategies.base import PlannedAction
from trading.strategies.recommendations import (
    record_recommendations,
    build_execution_plan_view,
    RecommendationActions,
)


class RecommendationHelpersTests(TestCase):
    def setUp(self):
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

        self.instrument = Instrument.objects.create(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="SMART",
            asset_type=Instrument.AssetType.EQUITY,
            currency="USD",
            is_active=True,
        )

        self.ibkr_con = IbkrContract.objects.create(
            con_id=999999,
            instrument=self.instrument,
            sec_type="STK",
            exchange="SMART",
            currency="USD",
            local_symbol="AAPL",
            last_trade_date_or_contract_month="",
            strike=None,
            right="",
            multiplier=None,
            metadata={},
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

        self.strategy_instance = StrategyInstance.objects.create(
            client=self.client_obj,
            name="Wheel v1 (Demo)",
            strategy_version=self.strategy_version,
            portfolio=self.portfolio,
            enabled=True,
            tags="test",
            config={},
        )

    def test_record_recommendations_basic(self):
        """
        record_recommendations should create Recommendation rows with
        normalized action name and correct FK fields populated.
        """
        asof_ts = timezone.now()

        action = PlannedAction(
            underlier=self.instrument,
            ibkr_con=self.ibkr_con,
            action="Sell Put",  # mixed case, space -> should normalize
            params={"strike": 150, "expiry": "2025-01-17"},
            confidence=Decimal("0.75"),
            rationale="Test recommendation",
            plan_id=None,
        )

        self.assertEqual(Recommendation.objects.count(), 0)

        recs = record_recommendations(
            strategy_instance=self.strategy_instance,
            strategy_version=self.strategy_version,
            client=self.client_obj,
            portfolio=self.portfolio,
            broker_account=self.broker_account,
            asof_ts=asof_ts,
            planned_actions=[action],
        )

        self.assertEqual(len(recs), 1)
        rec = recs[0]

        # Basic FK and scalar fields
        self.assertEqual(rec.client, self.client_obj)
        self.assertEqual(rec.portfolio, self.portfolio)
        self.assertEqual(rec.broker_account, self.broker_account)
        self.assertEqual(rec.strategy_instance, self.strategy_instance)
        self.assertEqual(rec.strategy_version, self.strategy_version)
        self.assertEqual(rec.underlier, self.instrument)
        self.assertEqual(rec.ibkr_con, self.ibkr_con)

        # Action string should be normalized to canonical form
        self.assertEqual(rec.action, RecommendationActions.SELL_PUT)

        self.assertEqual(rec.params["strike"], 150)
        self.assertEqual(rec.params["expiry"], "2025-01-17")
        self.assertEqual(rec.confidence, Decimal("0.75"))
        self.assertEqual(rec.rationale, "Test recommendation")
        self.assertIsNone(rec.plan_id)

    def test_build_execution_plan_view_groups_by_plan_id(self):
        """
        build_execution_plan_view should group recommendations by plan_id
        and sort items within each plan by confidence/action/asof_ts.
        """
        base_ts = timezone.now()

        plan_id = uuid.uuid4()

        # Two-step plan
        r1 = Recommendation.objects.create(
            client=self.client_obj,
            portfolio=self.portfolio,
            broker_account=self.broker_account,
            strategy_instance=self.strategy_instance,
            strategy_version=self.strategy_version,
            asof_ts=base_ts,
            underlier=self.instrument,
            ibkr_con=self.ibkr_con,
            action=RecommendationActions.SELL_PUT,
            params={"step": 1},
            confidence=Decimal("0.6"),
            rationale="Step 1",
            plan_id=plan_id,
        )

        r2 = Recommendation.objects.create(
            client=self.client_obj,
            portfolio=self.portfolio,
            broker_account=self.broker_account,
            strategy_instance=self.strategy_instance,
            strategy_version=self.strategy_version,
            asof_ts=base_ts + timezone.timedelta(seconds=1),
            underlier=self.instrument,
            ibkr_con=self.ibkr_con,
            action=RecommendationActions.BUY_STOCK,
            params={"step": 2},
            confidence=Decimal("0.8"),
            rationale="Step 2",
            plan_id=plan_id,
        )

        # Singleton recommendation (no plan_id)
        r3 = Recommendation.objects.create(
            client=self.client_obj,
            portfolio=self.portfolio,
            broker_account=self.broker_account,
            strategy_instance=self.strategy_instance,
            strategy_version=self.strategy_version,
            asof_ts=base_ts,
            underlier=self.instrument,
            ibkr_con=self.ibkr_con,
            action=RecommendationActions.DIAGNOSTIC,
            params={"foo": "bar"},
            confidence=Decimal("0.1"),
            rationale="Singleton",
            plan_id=None,
        )

        plan_view = build_execution_plan_view(
            Recommendation.objects.filter(strategy_instance=self.strategy_instance)
        )

        self.assertEqual(plan_view["total_recommendations"], 3)
        self.assertEqual(plan_view["total_plans"], 2)

        # Plans sorted by max_confidence desc: the two-step plan should come first
        plans = plan_view["plans"]
        first_plan = plans[0]
        second_plan = plans[1]

        self.assertEqual(first_plan["num_steps"], 2)
        self.assertEqual(second_plan["num_steps"], 1)

        # Within the first plan, the BUY_STOCK (higher confidence) should come first
        first_items = first_plan["items"]
        self.assertEqual(first_items[0]["action"], RecommendationActions.BUY_STOCK)
        self.assertEqual(first_items[0]["params"]["step"], 2)
        self.assertEqual(first_items[1]["action"], RecommendationActions.SELL_PUT)
        self.assertEqual(first_items[1]["params"]["step"], 1)
