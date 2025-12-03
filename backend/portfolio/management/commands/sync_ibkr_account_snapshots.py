# trading/management/commands/sync_ibkr_account_snapshots.py

from __future__ import annotations

from django.core.management.base import BaseCommand

from accounts.models import BrokerAccount
from trading.ingestion.accounts_sync import sync_account_snapshot_for_broker_account


class Command(BaseCommand):
    help = "Sync account snapshots from IBKR for all LIVE and PAPER_LINKED BrokerAccounts."

    def add_arguments(self, parser):
        parser.add_argument(
            "--account",
            "-a",
            dest="account_code",
            help="Optional: limit sync to a specific broker account_code (e.g. U1234567).",
        )

    def handle(self, *args, **options):
        account_code = options.get("account_code")

        qs = BrokerAccount.objects.filter(
            kind__in=[BrokerAccount.Kind.LIVE, BrokerAccount.Kind.PAPER_LINKED]
        )

        if account_code:
            qs = qs.filter(account_code=account_code)

        if not qs.exists():
            msg = "No matching BrokerAccount rows found."
            if account_code:
                msg += f" (for account_code={account_code!r})"
            self.stdout.write(self.style.WARNING(msg))
            return

        total = 0
        self.stdout.write(
            f"Syncing account snapshots for {qs.count()} broker account(s)..."
        )

        for ba in qs:
            self.stdout.write(f"  → {ba.account_code} ({ba.kind}) ... ", ending="")
            try:
                snapshot = sync_account_snapshot_for_broker_account(ba)
                total += 1
                self.stdout.write(self.style.SUCCESS("OK"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"FAILED: {e!r}"))

        self.stdout.write("")
        self.stdout.write(
            self.style.SUCCESS(f"Completed account snapshot sync. Created {total} snapshot(s).")
        )
