from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from accounts.models import BrokerAccount
from trading.ingestion.orders_sync import sync_orders_for_broker_account


class Command(BaseCommand):
    help = "Sync open orders from IBKR into the local Order model."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument(
            "--account",
            dest="account_code",
            type=str,
            help="Optional broker account code to limit sync to a single account.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        account_code = options.get("account_code")

        qs = BrokerAccount.objects.all()

        # You may choose to skip simulated accounts here:
        # qs = qs.exclude(kind=BrokerAccount.Kind.SIMULATED)
        # but we keep all kinds for now so Fake/SIM accounts can be used in tests.
        if account_code:
            qs = qs.filter(account_code=account_code)

        if not qs.exists():
            self.stdout.write(self.style.WARNING("No broker accounts found for sync."))
            return

        total_created = 0
        total_updated = 0

        for ba in qs:
            self.stdout.write(f"Syncing orders for account {ba.account_code}...")
            summary = sync_orders_for_broker_account(ba)
            total_created += summary.get("created", 0)
            total_updated += summary.get("updated", 0)
            self.stdout.write(
                f"  Created: {summary.get('created', 0)}, "
                f"Updated: {summary.get('updated', 0)}, "
                f"Total: {summary.get('total', 0)}"
            )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Total orders created={total_created}, updated={total_updated}."
            )
        )
