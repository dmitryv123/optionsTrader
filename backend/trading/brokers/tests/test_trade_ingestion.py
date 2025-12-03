#from datetime import datetime, timezone
from datetime import datetime, timezone as dt_timezone  # stdlib UTC, if you need it
from django.utils import timezone
from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from accounts.models import Client, BrokerAccount
from portfolio.models import Order, Execution, OptionEvent, IbkrContract, Instrument
from trading.brokers.testing import FakeBrokerAPI
from trading.brokers.types import OrderData, ExecutionData, OptionEventData
from trading.ingestion.orders_sync import sync_orders_for_broker_account
from trading.ingestion.executions_sync import sync_executions_for_broker_account
from trading.ingestion.option_events_sync import sync_option_events_for_broker_account


class OrdersIngestionTests(TestCase):
    def setUp(self) -> None:
        self.client_obj = Client.objects.create(name="Test Client")
        self.broker_account = BrokerAccount.objects.create(
            client=self.client_obj,
            kind=BrokerAccount.Kind.LIVE,
            account_code="UTEST",
            base_currency="USD",
            nickname="Test Account",
        )

    def _make_order_data(self, ibkr_order_id: int) -> OrderData:
        return OrderData(
            broker_account_code="UTEST",
            symbol="AAPL",
            con_id=12345,
            ibkr_order_id=ibkr_order_id,
            parent_ibkr_order_id=None,
            side="BUY",
            order_type="LMT",
            limit_price=Decimal("150.00"),
            aux_price=None,
            tif="DAY",
            status="Submitted",
            created_ts=timezone.now(), # datetime.utcnow(),
            updated_ts=timezone.now(), #datetime.utcnow(),
            raw={"source": "test"},
        )

    @patch("trading.ingestion.orders_sync.get_broker_client")
    def test_orders_ingestion_creates_and_updates(self, mock_get_client):
        # Arrange: fake broker returns one order
        fake = FakeBrokerAPI(
            # account_code="UTEST",
            orders=[self._make_order_data(ibkr_order_id=1)],
        )
        mock_get_client.return_value = fake

        # First sync: should create one Order
        summary1 = sync_orders_for_broker_account(self.broker_account)
        self.assertEqual(summary1["created"], 1)
        self.assertEqual(summary1["updated"], 0)
        self.assertEqual(Order.objects.count(), 1)

        order = Order.objects.get()
        self.assertEqual(order.ibkr_order_id, 1)
        self.assertEqual(order.side, "BUY")
        self.assertEqual(order.order_type, "LMT")

        # Second sync with same order but different status → update
        updated_order_data = self._make_order_data(ibkr_order_id=1)
        updated_order_data.status = "Filled"
        fake.orders = [updated_order_data]

        summary2 = sync_orders_for_broker_account(self.broker_account)
        self.assertEqual(summary2["created"], 0)
        self.assertEqual(summary2["updated"], 1)
        self.assertEqual(Order.objects.count(), 1)

        order.refresh_from_db()
        self.assertEqual(order.status, "Filled")


class ExecutionsIngestionTests(TestCase):
    def setUp(self) -> None:
        self.client_obj = Client.objects.create(name="Test Client")
        self.broker_account = BrokerAccount.objects.create(
            client=self.client_obj,
            kind=BrokerAccount.Kind.LIVE,
            account_code="UEXEC",
            base_currency="USD",
            nickname="Exec Account",
        )

        # We also need an Order to attach executions to
        self.order = Order.objects.create(
            client=self.client_obj,
            broker_account=self.broker_account,
            ibkr_con=None,
            ibkr_order_id=100,
            side="BUY",
            order_type="LMT",
            limit_price=Decimal("10.0"),
            aux_price=None,
            tif="DAY",
            status="Submitted",
            raw={},
            created_ts=timezone.now(), # datetime.utcnow(),
            updated_ts=timezone.now(), # datetime.utcnow(),
        )

    def _make_execution_data(self, exec_id: str) -> ExecutionData:
        return ExecutionData(
            broker_account_code="UEXEC",
            symbol="AAPL",
            con_id=12345,
            ibkr_exec_id=exec_id,
            ibkr_order_id=100,
            fill_ts=timezone.now(), # datetime.utcnow(),
            qty=Decimal("1"),
            price=Decimal("150"),
            fee=Decimal("0.5"),
            venue="TEST",
            raw={"source": "test"},
        )

    @patch("trading.ingestion.executions_sync.get_broker_client")
    def test_executions_ingestion_is_idempotent(self, mock_get_client):
        fake = FakeBrokerAPI(
            # account_code="UEXEC",
            executions=[self._make_execution_data(exec_id="E1")],
        )
        mock_get_client.return_value = fake

        # First sync: creates one Execution
        summary1 = sync_executions_for_broker_account(self.broker_account)
        self.assertEqual(summary1["created"], 1)
        self.assertEqual(summary1["skipped_existing"], 0)
        self.assertEqual(Execution.objects.count(), 1)

        # Second sync with same exec id: should be skipped
        summary2 = sync_executions_for_broker_account(self.broker_account)
        self.assertEqual(summary2["created"], 0)
        self.assertEqual(summary2["skipped_existing"], 1)
        self.assertEqual(Execution.objects.count(), 1)


class OptionEventsIngestionTests(TestCase):
    def setUp(self) -> None:
        self.client_obj = Client.objects.create(name="Test Client")
        self.broker_account = BrokerAccount.objects.create(
            client=self.client_obj,
            kind=BrokerAccount.Kind.LIVE,
            account_code="UOPT",
            base_currency="USD",
            nickname="Opt Account",
        )

        self.instrument = Instrument.objects.create(
            symbol="AAPL",
            name="Apple Inc.",
            exchange="SMART",
            asset_type=Instrument.AssetType.OPTION,
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

    def _make_option_event_data(self) -> OptionEventData:
        return OptionEventData(
            broker_account_code="UOPT",
            symbol="AAPL",
            con_id=self.ibkr_con.con_id,
            event_type="assignment",
            event_ts=timezone.now(), # datetime.utcnow(),
            qty=Decimal("1"),
            notes="Test assignment",
            raw={"source": "test"},
        )

    @patch("trading.ingestion.option_events_sync.get_broker_client")
    def test_option_events_ingestion_deduplicates(self, mock_get_client):
        ev_data = self._make_option_event_data()

        fake = FakeBrokerAPI(
            # account_code="UOPT",
            option_events=[ev_data],
        )
        mock_get_client.return_value = fake

        # First sync: create one OptionEvent
        summary1 = sync_option_events_for_broker_account(self.broker_account)
        self.assertEqual(summary1["created"], 1)
        self.assertEqual(summary1["skipped_existing"], 0)
        self.assertEqual(OptionEvent.objects.count(), 1)

        # Second sync with identical event: should be skipped
        summary2 = sync_option_events_for_broker_account(self.broker_account)
        self.assertEqual(summary2["created"], 0)
        self.assertEqual(summary2["skipped_existing"], 1)
        self.assertEqual(OptionEvent.objects.count(), 1)
