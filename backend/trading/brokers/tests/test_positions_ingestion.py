# trading/tests/test_positions_ingestion.py

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from accounts.models import Client, BrokerAccount
from portfolio.models import Portfolio, Instrument, IbkrContract, Position
from trading.brokers.testing import FakeBrokerAPI, make_simple_fake_position
from trading.ingestion.positions_sync import sync_positions_for_broker_account


class PositionsIngestionTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(name="TestClient")
        self.broker_account = BrokerAccount.objects.create(
            client=self.client_obj,
            kind=BrokerAccount.Kind.LIVE,
            account_code="U1234567",
            base_currency="USD",
            nickname="Test IBKR",
        )
        self.portfolio = Portfolio.objects.create(
            client=self.client_obj,
            name="Main",
            base_currency="USD",
            broker_account=self.broker_account,
        )

    def test_sync_positions_uses_fake_broker(self):
        fake_position = make_simple_fake_position(
            broker_account_code="U1234567",
            symbol="AAPL",
        )
        fake_broker = FakeBrokerAPI(positions=[fake_position])

        from trading.brokers import registry as registry_mod

        original_get_broker_client = registry_mod.get_broker_client

        def fake_get_broker_client(broker_account):
            return fake_broker

        try:
            registry_mod.get_broker_client = fake_get_broker_client

            created_count = sync_positions_for_broker_account(self.broker_account, portfolio=self.portfolio)
            self.assertEqual(created_count, 1)

            # Validate Position row
            self.assertEqual(Position.objects.count(), 1)
            pos = Position.objects.first()
            self.assertIsNotNone(pos)
            self.assertEqual(pos.client, self.client_obj)
            self.assertEqual(pos.broker_account, self.broker_account)
            self.assertEqual(pos.portfolio, self.portfolio)
            self.assertEqual(pos.instrument.symbol, "AAPL")
            self.assertEqual(pos.qty, Decimal("10"))
            self.assertEqual(pos.market_value, Decimal("1700.00"))

            # Instrument and IbkrContract should be created
            self.assertEqual(Instrument.objects.count(), 1)
            self.assertEqual(IbkrContract.objects.count(), 1)
            contract = IbkrContract.objects.first()
            self.assertEqual(contract.con_id, fake_position.con_id)
            self.assertEqual(contract.instrument, pos.instrument)
        finally:
            registry_mod.get_broker_client = original_get_broker_client
