# trading/ingestion/accounts_sync.py

from __future__ import annotations

from typing import Optional

from django.db import transaction

from accounts.models import BrokerAccount, AccountSnapshot
from trading.brokers.registry import get_broker_client


@transaction.atomic
def sync_account_snapshot_for_broker_account(broker_account: BrokerAccount,) -> AccountSnapshot:
    """
    Fetch the latest account snapshot from the underlying broker
    and persist it as an AccountSnapshot row.

    This is the primary ingestion entry point for EPIC 2 (accounts).

    Workflow:
      1. Resolve BrokerAPI via get_broker_client(broker_account)
      2. Call fetch_account_snapshots()
      3. Take the first (and typically only) snapshot
      4. Create a new AccountSnapshot row

    Raises:
        RuntimeError: if no snapshot data is returned by the broker.
    """
    client = get_broker_client(broker_account)
    # print ('client',client)
    snapshots = list(client.fetch_account_snapshots())

    if not snapshots:
        raise RuntimeError(
            f"No account snapshot data returned for broker account "
            f"{broker_account.account_code!r}"
        )

    data = snapshots[0]

    obj = AccountSnapshot.objects.create(
        client=broker_account.client,
        broker_account=broker_account,
        asof_ts=data.asof_ts,
        currency=data.currency,
        cash=data.cash,
        buying_power=data.buying_power,
        maintenance_margin=data.maintenance_margin,
        used_margin=data.used_margin,
        extras=data.extras,
    )
    # print ('obj.extras',obj.extras, 'currency',obj.currency, 'obj.buying_power',obj.buying_power,)
    return obj


def sync_all_ibkr_account_snapshots() -> int:
    """
    Convenience helper: sync snapshots for all IBKR-backed BrokerAccount rows.

    Returns:
        Number of AccountSnapshot rows created.

    Notes:
        - Currently filters on LIVE and PAPER_LINKED kinds.
        - Intended for use by management commands or scheduled jobs.
    """
    from accounts.models import BrokerAccount  # local import to avoid cycles

    accounts = BrokerAccount.objects.filter(
        kind__in=[
            BrokerAccount.Kind.LIVE,
            BrokerAccount.Kind.PAPER_LINKED,
        ]
    )

    created_count = 0
    for ba in accounts:
        # Let errors surface; we usually want failures visible in logs.
        sync_account_snapshot_for_broker_account(ba)
        created_count += 1

    return created_count
