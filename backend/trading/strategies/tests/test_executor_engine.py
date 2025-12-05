from __future__ import annotations

from decimal import Decimal

from django.test import TestCase
from django.utils import timezone

from accounts.models import Client, BrokerAccount
from portfolio.models import Portfolio
from strategies.models import StrategyDefinition, StrategyVersion, StrategyInstance, StrategyRun
from trading.strategies.base import BaseStrategy, PlannedAction
from trading.strategies.executor import run_strategy_instance


# Fake strategy for testing the engine only (not Wheel logic itself)
class FakeHappyStrategy(BaseStrategy):
    """
    Minimal strategy that always emits one PlannedAction.
    Used to test the StrategyEngine happy path.
    """

    def run(self, context):
        return [
            PlannedAction(
                underlier=None,
                ibkr_con=None,
                action="diagnostic",
                params={"foo": "bar"},
                confidence=Decimal("0.5"),
                rationale="Happy path",
                plan_id=None,
            )
        ]


class FakeErrorStrategy(BaseStrategy):
    """
    Strategy that raises an exception to test error handling and
    StrategyRun.status='error'.
    """

    def run(self, context):
        raise RuntimeError("Synthetic failure in FakeErrorStrategy")


class StrategyEngineTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(
            name="Engine Test Client",
            is_active=True,
            settings={},
        )

        self.broker_account = BrokerAccount.objects.create(
            client=self.client_obj,
            kind=BrokerAccount.Kind.SIMULATED,
            account_code="U999999",
            base_currency="USD",
            nickname="SIM",
            metadata={},
        )

        self.portfolio = Portfolio.objects.create(
            client=self.client_obj,
            name="Engine Test Portfolio",
            base_currency="USD",
            broker_account=self.broker_account,
            metadata={},
        )

        # Definition & Version for fake strategies
        self.strategy_def = StrategyDefinition.objects.create(
            name="FakeEngineTest",
            slug="fake-engine",
            description="Engine test strategies",
        )

    def _make_version_and_instance(self, cls_path: str) -> StrategyInstance:
        version = StrategyVersion.objects.create(
            strategy_def=self.strategy_def,
            version="v1",
            code_ref=cls_path,
            schema={},
        )
        instance = StrategyInstance.objects.create(
            client=self.client_obj,
            name=f"Instance for {cls_path}",
            strategy_version=version,
            portfolio=self.portfolio,
            enabled=True,
            tags="test",
            config={},
        )
        return instance

    def test_run_strategy_happy_path_creates_run_and_actions(self):
        """
        T0060.1 + T0060.3:
        - run_strategy_instance should create a StrategyRun row
        - status should be 'ok'
        - at least one action is returned
        """
        instance = self._make_version_and_instance(
            "trading.strategies.tests.test_executor_engine:FakeHappyStrategy"
        )

        asof_ts = timezone.now()
        actions = run_strategy_instance(instance, asof_ts=asof_ts, persist_recommendations=False)

        self.assertGreaterEqual(len(actions), 1)

        runs = StrategyRun.objects.filter(strategy_instance=instance)
        self.assertEqual(runs.count(), 1)
        run = runs.first()
        self.assertEqual(run.status, "ok")
        self.assertIn("num_actions", run.stats)
        self.assertEqual(run.stats["num_actions"], len(actions))

    def test_run_strategy_error_sets_status_error_and_run_exists(self):
        """
        T0060.2 + T0060.3:
        - If the strategy raises, StrategyRun.status must be 'error'
        - A StrategyRun row is still created even when there is an error.
        """
        instance = self._make_version_and_instance(
            "trading.strategies.tests.test_executor_engine:FakeErrorStrategy"
        )

        with self.assertRaises(RuntimeError):
            run_strategy_instance(instance, persist_recommendations=False)

        runs = StrategyRun.objects.filter(strategy_instance=instance)
        self.assertEqual(runs.count(), 1)
        run = runs.first()
        self.assertEqual(run.status, "error")
        self.assertTrue(run.error_trace)
