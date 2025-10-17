from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone
from decimal import Decimal

from accounts.models import Client, ClientMembership, BrokerAccount, AccountSnapshot
from portfolio.models import Portfolio, Instrument, IbkrContract


class Command(BaseCommand):
    help = "Seed demo client, user, broker account, portfolio, instrument, contract, and account snapshot"

    def handle(self, *args, **options):
        User = get_user_model()

        # 1) Demo user (idempotent)
        user, _ = User.objects.get_or_create(
            username="demo_user",
            defaults={"email": "demo@example.com"},
        )
        if not user.has_usable_password():
            user.set_password("demopass")
            user.save()

        # 2) Client (CREATE if missing)
        client, _ = Client.objects.get_or_create(
            name="Demo Client",
            defaults={"is_active": True, "settings": {}},
        )

        # 3) Membership (OWNER)
        ClientMembership.objects.get_or_create(
            client=client,
            user=user,
            defaults={"role": ClientMembership.Role.OWNER},
        )

        # 4) BrokerAccount (paper)
        broker, _ = BrokerAccount.objects.get_or_create(
            client=client,
            kind=BrokerAccount.Kind.LIVE,
            account_code="DU1234567",
            defaults={"nickname": "Real Account", "base_currency": "USD"}, # "metadata": {}},
        )

        # 5) Portfolio
        portfolio, _ = Portfolio.objects.get_or_create(
            client=client,
            broker_account=broker,
            name="Main Portfolio",
            defaults={"base_currency": "USD", "metadata": {}},
        )

        # 6) Instrument + IBKR Contract (AAPL example)
        aapl, _ = Instrument.objects.get_or_create(
            symbol="AAPL",
            asset_type=Instrument.AssetType.EQUITY,
            currency="USD",
            defaults={"name": "Apple Inc.", "exchange": "NASDAQ", "is_active": True},
        )
        IbkrContract.objects.get_or_create(
            con_id=265598,              # example conId for AAPL
            instrument=aapl,
            defaults={
                "sec_type": "STK",
                "exchange": "NASDAQ",
                "currency": "USD",
                "local_symbol": "AAPL",
                "last_trade_date_or_contract_month": "",
                "strike": None,
                "right": "",
                "multiplier": None,
                "metadata": {},
            },
        )

        # 7) Account snapshot
        AccountSnapshot.objects.get_or_create(
            client=client,
            broker_account=broker,
            asof_ts=timezone.now(),
            defaults={
                "currency": "USD",
                "cash": Decimal("25000"),
                "buying_power": Decimal("100000"),
                "maintenance_margin": Decimal("15000"),
                "used_margin": Decimal("5000"),
                "extras": {"note": "demo snapshot"},
            },
        )

        self.stdout.write(self.style.SUCCESS("✅ Demo tenant, user, broker, portfolio, instrument, contract, snapshot seeded."))

