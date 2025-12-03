from __future__ import annotations

from typing import Dict

from django.db import transaction

from accounts.models import BrokerAccount
from portfolio.models import Order, IbkrContract
from trading.brokers.registry import get_broker_client
from trading.brokers.types import OrderData


@transaction.atomic
def sync_orders_for_broker_account(broker_account: BrokerAccount) -> Dict[str, int]:
    """
    Ingest open (and recent) orders for a single BrokerAccount.

    Idempotent upsert semantics:
      - Uses (broker_account, ibkr_order_id) as the natural key
      - On re-run, updates status/price/timestamps on existing rows
      - Does not create duplicates

    Returns a summary dict:
      {"created": X, "updated": Y, "total": X+Y}
    """
    client = get_broker_client(broker_account)

    created = 0
    updated = 0

    for od in client.fetch_open_orders():
        # Safety: if the normalized dataclass carries an account code, ensure it matches.
        if od.broker_account_code and od.broker_account_code != broker_account.account_code:
            # Skip mismatched records; this should not normally happen.
            continue

        # Try to resolve IBKR contract if we have con_id
        ibkr_con = None
        if od.con_id is not None:
            ibkr_con = IbkrContract.objects.filter(con_id=od.con_id).first()

        defaults = {
            "client": broker_account.client,
            "ibkr_con": ibkr_con,
            "side": od.side,
            "order_type": od.order_type,
            "limit_price": od.limit_price,
            "aux_price": od.aux_price,
            "tif": od.tif,
            "status": od.status,
            "raw": od.raw,
            "created_ts": od.created_ts,
            "updated_ts": od.updated_ts,
        }

        order_obj, is_created = Order.objects.update_or_create(
            broker_account=broker_account,
            ibkr_order_id=od.ibkr_order_id,
            defaults=defaults,
        )

        if is_created:
            created += 1
        else:
            updated += 1

    return {"created": created, "updated": updated, "total": created + updated}
