from __future__ import annotations

from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from accounts.models import BrokerAccount
from trading.ingestion.option_events_sync import sync_option_events_for_broker_account


class Command(BaseCommand):
    help = "Sync option lifecycle events from IBKR into the local OptionEvent model."

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
            if account_code:
                qs = qs.filter(account_code=account_code)

            if not qs.exists():
                self.stdout.write(self.style.WARNING("No broker accounts found for sync."))
                return

            total_created = 0
            total_skipped = 0

            for ba in qs:
                self.stdout.write(f"Syncing option events for account {ba.account_code}...")
                summary = sync_option_events_for_broker_account(ba)
                total_created += summary.get("created", 0)
                total_skipped += summary.get("skipped_existing", 0)
                self.stdout.write(
                    f"  Created: {summary.get('created', 0)}, "
                    f"Skipped existing: {summary.get('skipped_existing', 0)}, "
                    f"Total: {summary.get('total', 0)}"
                )

            self.stdout.write(
                self.style.SUCCESS(
                    f"Done. Total option events created={total_created}, "
                    f"skipped_existing={total_skipped}."
                )
            )
