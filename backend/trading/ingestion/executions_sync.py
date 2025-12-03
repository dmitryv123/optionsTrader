from __future__ import annotations

from typing import Dict

from django.db import transaction

from accounts.models import BrokerAccount
from portfolio.models import Order, Execution
from trading.brokers.registry import get_broker_client
from trading.brokers.types import ExecutionData


@transaction.atomic
def sync_executions_for_broker_account(broker_account: BrokerAccount) -> Dict[str, int]:
    """
    Ingest executions (fills) for a single BrokerAccount.

    Idempotency:
      - Execution.ibkr_exec_id is unique
      - If an execution with the same ibkr_exec_id already exists, we skip it
        instead of creating a duplicate.

    Returns:
      {"created": X, "skipped_existing": Y, "total": X+Y}
    """
    client = get_broker_client(broker_account)

    created = 0
    skipped_existing = 0

    for ed in client.fetch_executions():
        if ed.broker_account_code and ed.broker_account_code != broker_account.account_code:
            continue

        # Idempotency: skip if already seen
        if Execution.objects.filter(ibkr_exec_id=ed.ibkr_exec_id).exists():
            skipped_existing += 1
            continue

        order_obj = None
        if ed.ibkr_order_id is not None:
            order_obj = (
                Order.objects.filter(
                    broker_account=broker_account,
                    ibkr_order_id=ed.ibkr_order_id,
                )
                .order_by("-created_ts")
                .first()
            )

        # Execution.order is non-nullable; if we cannot resolve an order,
        # we have a few options: skip, log, or raise. For now we SKIP.
        if order_obj is None:
            # Later you can plug in logging here if desired.
            skipped_existing += 1
            continue

        Execution.objects.create(
            client=broker_account.client,
            order=order_obj,
            ibkr_exec_id=ed.ibkr_exec_id,
            fill_ts=ed.fill_ts,
            qty=ed.qty,
            price=ed.price,
            fee=ed.fee,
            venue=ed.venue,
            raw=ed.raw,
        )
        created += 1

    return {
        "created": created,
        "skipped_existing": skipped_existing,
        "total": created + skipped_existing,
    }
