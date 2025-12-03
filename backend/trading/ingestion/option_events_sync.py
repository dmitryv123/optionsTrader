from __future__ import annotations

from typing import Dict

from django.db import transaction

from accounts.models import BrokerAccount
from portfolio.models import OptionEvent, IbkrContract
from trading.brokers.registry import get_broker_client
from trading.brokers.types import OptionEventData


@transaction.atomic
def sync_option_events_for_broker_account(broker_account: BrokerAccount) -> Dict[str, int]:
    """
    Ingest option lifecycle events (assignment/exercise/expiration) for
    a single BrokerAccount.

    Deduplication:
      - Uses a natural key (broker_account, ibkr_con, event_type, event_ts, qty)
        to detect duplicates and avoid inserting them twice.

    Returns:
      {"created": X, "skipped_existing": Y, "total": X+Y}
    """
    client = get_broker_client(broker_account)

    created = 0
    skipped_existing = 0

    for ev in client.fetch_option_events():
        if ev.broker_account_code and ev.broker_account_code != broker_account.account_code:
            continue

        ibkr_con = None
        if ev.con_id is not None:
            ibkr_con = IbkrContract.objects.filter(con_id=ev.con_id).first()

        # Natural de-dup key: broker_account + contract + type + ts + qty
        exists = OptionEvent.objects.filter(
            client=broker_account.client,
            broker_account=broker_account,
            ibkr_con=ibkr_con,
            event_type=ev.event_type,
            event_ts=ev.event_ts,
            qty=ev.qty,
        ).exists()

        if exists:
            skipped_existing += 1
            continue

        OptionEvent.objects.create(
            client=broker_account.client,
            broker_account=broker_account,
            ibkr_con=ibkr_con,
            event_type=ev.event_type,
            event_ts=ev.event_ts,
            qty=ev.qty,
            notes=ev.notes,
        )
        created += 1

    return {
        "created": created,
        "skipped_existing": skipped_existing,
        "total": created + skipped_existing,
    }
