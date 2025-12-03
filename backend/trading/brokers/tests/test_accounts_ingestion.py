# trading/tests/test_accounts_ingestion.py

from __future__ import annotations

from decimal import Decimal

from django.test import TestCase

from accounts.models import Client, BrokerAccount, AccountSnapshot
from trading.brokers.testing import FakeBrokerAPI, make_simple_fake_account_snapshot
from trading.ingestion.accounts_sync import sync_account_snapshot_for_broker_account


class AccountIngestionTests(TestCase):
    def setUp(self):
        self.client_obj = Client.objects.create(name="TestClient")
        self.broker_account = BrokerAccount.objects.create(
            client=self.client_obj,
            kind=BrokerAccount.Kind.LIVE,
            account_code="U1234567",
            base_currency="USD",
            nickname="Test IBKR",
        )

    def test_sync_account_snapshot_uses_fake_broker(self):
        fake_snapshot = make_simple_fake_account_snapshot(broker_account_code="U1234567")
        # print ('test_sync_account_snapshot_uses_fake_broker fake_snapshot:', fake_snapshot)
        fake_broker = FakeBrokerAPI(account_snapshots=[fake_snapshot])
        # print ('fake_broker',fake_broker)

        # Monkeypatch get_broker_client to return our fake for this test
        from trading import brokers as brokers_pkg  # root package
        from trading.brokers import registry as registry_mod

        original_get_broker_client = registry_mod.get_broker_client

        # print ('original_get_broker_client',original_get_broker_client)

        def fake_get_broker_client(broker_account):
            return fake_broker

        try:
            registry_mod.get_broker_client = fake_get_broker_client

            snapshot_obj = sync_account_snapshot_for_broker_account(self.broker_account)

            self.assertEqual(snapshot_obj.client, self.client_obj)
            self.assertEqual(snapshot_obj.broker_account, self.broker_account)
            self.assertEqual(snapshot_obj.currency, fake_snapshot.currency)
            self.assertEqual(snapshot_obj.cash, Decimal("100000"))
            self.assertEqual(snapshot_obj.buying_power, Decimal("300000"))
            self.assertIn("account_code", snapshot_obj.extras)
            self.assertEqual(snapshot_obj.extras["account_code"], "U1234567")
            self.assertEqual(AccountSnapshot.objects.count(), 1)
        finally:
            # Restore original implementation
            registry_mod.get_broker_client = original_get_broker_client
