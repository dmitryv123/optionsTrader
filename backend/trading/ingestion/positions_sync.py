# trading/ingestion/positions_sync.py

from __future__ import annotations

from typing import Tuple, Optional, Iterable

from django.db import transaction

from accounts.models import BrokerAccount
from portfolio.models import Instrument, IbkrContract, Portfolio, Position
from trading.brokers.registry import get_broker_client
from trading.brokers.types import PositionData


def get_or_create_instrument_and_contract(
    pos_data: PositionData,
) -> Tuple[Instrument, Optional[IbkrContract]]:
    """
    Given normalized PositionData, resolve or create Instrument and IbkrContract.

    This is the only place where symbol/exchange/asset_type/currency are mapped
    into the Instrument model, and where con_id is mapped to IbkrContract.
    """
    # Normalize exchange to empty string when missing for uniqueness consistency
    exchange = pos_data.exchange or ""

    instrument, _ = Instrument.objects.get_or_create(
        symbol=pos_data.symbol,
        exchange=exchange,
        asset_type=pos_data.asset_type,
        currency=pos_data.currency,
    )

    ibkr_con: Optional[IbkrContract] = None
    if pos_data.con_id is not None:
        ibkr_con, created = IbkrContract.objects.get_or_create(
            con_id=pos_data.con_id,
            defaults={
                "instrument": instrument,
                "sec_type": "STK" if pos_data.asset_type == Instrument.AssetType.EQUITY else "OPT",
                "exchange": exchange,
                "currency": pos_data.currency,
                "local_symbol": pos_data.raw.get("local_symbol", ""),
                "last_trade_date_or_contract_month": pos_data.raw.get(
                    "last_trade_date_or_contract_month", ""
                ),
                "strike": pos_data.raw.get("strike"),
                "right": pos_data.raw.get("right", ""),
                "multiplier": pos_data.raw.get("multiplier"),
                "metadata": pos_data.raw,
            },
        )

        # If the contract already existed but had a different instrument, align it.
        if not created and ibkr_con.instrument_id != instrument.id:
            ibkr_con.instrument = instrument
            ibkr_con.save(update_fields=["instrument"])

    return instrument, ibkr_con


@transaction.atomic
def sync_positions_for_broker_account(
    broker_account: BrokerAccount,
    portfolio: Optional[Portfolio] = None,
) -> int:
    """
    Fetch current positions from the broker and persist Position snapshots.

    Args:
        broker_account: The BrokerAccount whose positions are to be synced.
        portfolio: Optional explicit Portfolio. If not provided, the first
                   portfolio associated with this BrokerAccount will be used.

    Returns:
        Number of Position rows created in this sync run.

    Notes:
        - This function assumes snapshot-style storage: each run records a new
          snapshot with its own asof_ts per instrument.
        - It does not delete or update previous Position rows.
    """
    if portfolio is None:
        portfolio = broker_account.portfolios.first()
        if portfolio is None:
            raise RuntimeError(
                f"No portfolio associated with broker account {broker_account.account_code!r}"
            )

    client = get_broker_client(broker_account)
    positions_data: Iterable[PositionData] = client.fetch_positions()

    created_count = 0

    for pd in positions_data:
        instrument, ibkr_con = get_or_create_instrument_and_contract(pd)

        Position.objects.create(
            client=broker_account.client,
            portfolio=portfolio,
            broker_account=broker_account,
            instrument=instrument,
            ibkr_con=ibkr_con,
            qty=pd.qty,
            avg_cost=pd.avg_cost,
            market_price=pd.market_price,
            market_value=pd.market_value,
            asof_ts=pd.asof_ts,
        )
        created_count += 1

    return created_count
