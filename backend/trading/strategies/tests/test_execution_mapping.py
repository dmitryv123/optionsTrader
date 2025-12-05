# backend/trading/strategies/tests/test_execution_mapping.py

from decimal import Decimal
from uuid import uuid4

from django.test import TestCase

from accounts.models import Client, BrokerAccount
from portfolio.models import Instrument, IbkrContract
# from trading.strategies.types import PlannedAction
from trading.strategies.base import PlannedAction
from trading.strategies.execution_intents import ExecutionIntent
from trading.strategies.execution_mapping import (
    ExecutionMappingError,
    map_planned_action_to_execution_intent,
)


class DummyContext:
    """
    Minimal context object for tests.

    Only exposes .broker_account.account_code, which is all the mapper needs.
    """

    def __init__(self, broker_account: BrokerAccount):
        self.broker_account = broker_account


class ExecutionMappingTests(TestCase):
    def setUp(self) -> None:
        self.client = Client.objects.create(name="Demo Client")
        self.broker_account = BrokerAccount.objects.create(
            client=self.client,
            kind=BrokerAccount.Kind.SIMULATED,
            account_code="U1234567",
            base_currency="USD",
        )

        self.instrument = Instrument.objects.create(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="SMART",
            asset_type=Instrument.AssetType.EQUITY,
            currency="USD",
        )

        self.ibkr_con = IbkrContract.objects.create(
            con_id=999999,
            instrument=self.instrument,
            sec_type="OPT",
            exchange="SMART",
            currency="USD",
            local_symbol="AAPL  240621C00150000",
            last_trade_date_or_contract_month="20240621",
            strike=Decimal("150"),
            right="C",
            multiplier=100,
            metadata={},
        )

        self.context = DummyContext(self.broker_account)

    def test_happy_path_sell_put_limit_order(self):
        """
        T0183.4 — Happy path:
        - action='sell_put'
        - has qty, limit_price, tif
        - has ibkr_con
        Expect ExecutionIntent with correct side, quantity, limit_price, etc.
        """
        action = PlannedAction(
            underlier=None,
            action="sell_put",
            params={
                "qty": 1,
                "limit_price": Decimal("2.50"),
                "tif": "GTC",
            },
            ibkr_con=self.ibkr_con,
            confidence=Decimal("0.7"),
            rationale="Test short put",
            plan_id=uuid4(),
        )

        intent = map_planned_action_to_execution_intent(action, self.context)

        self.assertIsInstance(intent, ExecutionIntent)
        self.assertEqual(intent.broker_account_code, "U1234567")
        self.assertEqual(intent.con_id, self.ibkr_con.con_id)
        self.assertEqual(intent.side, "SELL")
        self.assertEqual(intent.order_type, "LMT")
        self.assertEqual(intent.quantity, Decimal("1"))
        self.assertEqual(intent.limit_price, Decimal("2.50"))
        self.assertEqual(intent.tif, "GTC")
        self.assertEqual(intent.action, "sell_put")
        self.assertEqual(intent.notes, "Test short put")
        self.assertEqual(intent.raw_params["qty"], 1)

    def test_non_executable_action_raises(self):
        """
        Non-order actions like 'diagnostic' should raise ExecutionMappingError.
        """
        action = PlannedAction(
            underlier=None,
            action="diagnostic",
            params={"foo": "bar"},
            ibkr_con=None,
            confidence=Decimal("0"),
            rationale="Just diagnostics",
            plan_id=None,
        )

        with self.assertRaises(ExecutionMappingError):
            map_planned_action_to_execution_intent(action, self.context)

    def test_missing_quantity_raises(self):
        """
        Missing or zero quantity should raise ExecutionMappingError.
        """
        action = PlannedAction(
            underlier=None,
            action="sell_put",
            params={"limit_price": Decimal("2.50")},  # no qty
            ibkr_con=self.ibkr_con,
            confidence=Decimal("0.5"),
            rationale="No qty",
            plan_id=None,
        )

        with self.assertRaises(ExecutionMappingError):
            map_planned_action_to_execution_intent(action, self.context)

    def test_missing_con_id_raises(self):
        """
        If neither ibkr_con nor con_id is present, the mapper should refuse
        to produce an ExecutionIntent.
        """
        action = PlannedAction(
            underlier=None,
            action="sell_put",
            params={"qty": 1},  # no con_id, no ibkr_con
            ibkr_con=None,
            confidence=Decimal("0.5"),
            rationale="No con_id",
            plan_id=None,
        )

        with self.assertRaises(ExecutionMappingError):
            map_planned_action_to_execution_intent(action, self.context)
