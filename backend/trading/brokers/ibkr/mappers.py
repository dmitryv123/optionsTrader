# trading/brokers/ibkr/mappers.py

from __future__ import annotations
from dataclasses import asdict, dataclass
# from datetime import datetime, timezone
from datetime import datetime, timezone as dt_timezone  # stdlib UTC, if you need it
from django.utils import timezone
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional

from trading.brokers.types import (AccountSnapshotData,
                                   PositionData,
                                   OrderData,
                                   ExecutionData,
                                   OptionEventData)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _to_decimal(value: Any, default: str = "0") -> Decimal:
    """
    Best-effort conversion to Decimal.

    Accepts str, int, float, Decimal, or None. Falls back to `default`
    (as string) when value is None or empty.
    """
    if value is None:
        return Decimal(default)

    if isinstance(value, Decimal):
        return value

    # Some brokers return "" or " " for missing numeric fields
    s = str(value).strip()
    if not s:
        return Decimal(default)

    return Decimal(s)


def _to_datetime(value: Any) -> datetime:
    """
    Normalize various timestamp representations to an aware UTC datetime.

    For now, if value is None or unrecognized, we fall back to `datetime.now(UTC)`.
    Later, this can be extended to parse broker-specific timestamp formats.
    """
    if isinstance(value, datetime):
        # If naive, assume UTC; if aware, keep as is
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value

    # TODO: parse strings like "2025-09-25T15:22:46Z" if broker provides them
    return timezone.now()  # datetime.now(timezone.utc)


# ---------------------------------------------------------------------------
# Account mapping
# ---------------------------------------------------------------------------

def map_raw_account_to_snapshot(raw: Any, account_code: str) -> AccountSnapshotData:
    """
    Map a raw IBKR account payload to AccountSnapshotData.

    The `raw` input is expected to be a dict-like object, as produced by
    IBKRTransport.fetch_raw_account_data(). For T0029/T0030, this might be
    the stub dict; later it will be a real IBKR payload (ib_insync / REST).

    Required keys (by convention, not strictly enforced at this layer):
      - "currency"
      - "cash"
      - "buying_power"
      - "maintenance_margin"
      - "used_margin"
      - "timestamp" (optional)

    Any extra fields are preserved in `extras` for debugging/analysis.
    """
    # Ensure we have a dict for extras preservation
    if not isinstance(raw, dict):
        raw = {"_raw": raw}

    currency = raw.get("currency", "USD")
    cash = _to_decimal(raw.get("cash"))
    buying_power = _to_decimal(raw.get("buying_power"))
    maintenance_margin = _to_decimal(raw.get("maintenance_margin"))
    used_margin = _to_decimal(raw.get("used_margin"))
    asof_ts = _to_datetime(raw.get("timestamp"))

    snapshot = AccountSnapshotData(
        broker_account_code=account_code,
        currency=currency,
        asof_ts=asof_ts,
        cash=cash,
        buying_power=buying_power,
        maintenance_margin=maintenance_margin,
        used_margin=used_margin,
        extras=raw,
    )
    return snapshot


# ---------------------------------------------------------------------------
# Positions mapping
# ---------------------------------------------------------------------------

def map_raw_positions(raw_positions: Iterable[Any], account_code: str) -> List[PositionData]:
    """
    Map a sequence of raw IBKR position payloads into a list of PositionData.

    Each raw item is expected to be a dict-like object with at least:
      - "symbol"
      - "exchange" (optional)
      - "asset_type" (e.g. "equity", "option")
      - "currency"  (default: "USD")
      - "con_id"    (optional)
      - "qty"
      - "avg_cost"
      - "market_price"
      - "market_value"
      - "timestamp" (optional)

    The entire raw dict is stored in `raw` for each PositionData.
    """
    result: List[PositionData] = []

    for raw in raw_positions:
        if not isinstance(raw, dict):
            raw = {"_raw": raw}

        symbol = raw.get("symbol", "")
        exchange = raw.get("exchange")
        asset_type = raw.get("asset_type", "equity")
        currency = raw.get("currency", "USD")

        con_id = raw.get("con_id")
        # Some APIs might return con_id as string — normalize to int if possible
        if isinstance(con_id, str) and con_id.isdigit():
            con_id = int(con_id)

        qty = _to_decimal(raw.get("qty"))
        avg_cost = _to_decimal(raw.get("avg_cost"))
        market_price = _to_decimal(raw.get("market_price"))
        market_value = _to_decimal(raw.get("market_value"))
        asof_ts = _to_datetime(raw.get("timestamp"))

        pos = PositionData(
            broker_account_code=account_code,
            symbol=symbol,
            exchange=exchange,
            asset_type=asset_type,
            currency=currency,
            con_id=con_id,
            qty=qty,
            avg_cost=avg_cost,
            market_price=market_price,
            market_value=market_value,
            asof_ts=asof_ts,
            raw=raw,
        )
        result.append(pos)

    return result


def map_raw_orders(raw_orders: Iterable[Dict[str, Any]], account_code: str) -> List[OrderData]:
    """
    Map raw IBKR order payloads into normalized OrderData objects.

    For now this assumes raw_orders is an iterable of dict-like objects with
    keys such as:
      - "symbol"
      - "con_id"
      - "order_id"
      - "parent_id"
      - "side"
      - "order_type"
      - "limit_price"
      - "aux_price"
      - "tif"
      - "status"
      - "created_ts"
      - "updated_ts"

    When wiring real IBKR, adjust these key lookups in one place.
    """
    results: List[OrderData] = []

    for raw in raw_orders:
        symbol = raw.get("symbol", "")
        con_id = raw.get("con_id")
        order_id = raw.get("order_id")
        parent_id = raw.get("parent_id")

        created_ts = _to_datetime(raw.get("created_ts")) or timezone.now()  # datetime.utcnow()
        updated_ts = _to_datetime(raw.get("updated_ts")) or created_ts

        order = OrderData(
            broker_account_code=account_code,
            symbol=symbol,
            con_id=int(con_id) if con_id is not None else None,
            ibkr_order_id=int(order_id),
            parent_ibkr_order_id=int(parent_id) if parent_id is not None else None,
            side=str(raw.get("side", "")).upper(),
            order_type=str(raw.get("order_type", "")).upper(),
            limit_price=_to_decimal(raw.get("limit_price")),
            aux_price=_to_decimal(raw.get("aux_price")),
            tif=str(raw.get("tif", "")),
            status=str(raw.get("status", "")),
            created_ts=created_ts,
            updated_ts=updated_ts,
            raw=dict(raw),
        )
        results.append(order)

    return results


def map_raw_executions(raw_execs: Iterable[Dict[str, Any]], account_code: str) -> List[ExecutionData]:
    """
    Map raw IBKR execution payloads into normalized ExecutionData objects.

    Expected keys (adjust later as needed):
      - "symbol"
      - "con_id"
      - "exec_id"
      - "order_id"
      - "fill_ts"
      - "qty"
      - "price"
      - "fee"
      - "venue"
    """
    results: List[ExecutionData] = []

    for raw in raw_execs:
        symbol = raw.get("symbol", "")
        con_id = raw.get("con_id")
        exec_id = raw.get("exec_id")
        order_id = raw.get("order_id")

        fill_ts = _to_datetime(raw.get("fill_ts")) or timezone.now() # datetime.utcnow()

        execution = ExecutionData(
            broker_account_code=account_code,
            symbol=symbol,
            con_id=int(con_id) if con_id is not None else None,
            ibkr_exec_id=str(exec_id),
            ibkr_order_id=int(order_id) if order_id is not None else None,
            fill_ts=fill_ts,
            qty=_to_decimal(raw.get("qty")) or Decimal("0"),
            price=_to_decimal(raw.get("price")) or Decimal("0"),
            fee=_to_decimal(raw.get("fee")) or Decimal("0"),
            venue=str(raw.get("venue", "")),
            raw=dict(raw),
        )
        results.append(execution)

    return results


def map_raw_option_events(raw_events: Iterable[Dict[str, Any]], account_code: str) -> List[OptionEventData]:
    """
    Map raw IBKR option lifecycle events into OptionEventData objects.

    Expected keys (adjust later as needed):
      - "symbol"
      - "con_id"
      - "event_type"
      - "event_ts"
      - "qty"
      - "notes"
    """
    results: List[OptionEventData] = []

    for raw in raw_events:
        symbol = raw.get("symbol", "")
        con_id = raw.get("con_id")
        event_type = str(raw.get("event_type", "")).lower()
        event_ts = _to_datetime(raw.get("event_ts")) or timezone.now() # datetime.utcnow()

        event = OptionEventData(
            broker_account_code=account_code,
            symbol=symbol,
            con_id=int(con_id) if con_id is not None else None,
            event_type=event_type,
            event_ts=event_ts,
            qty=_to_decimal(raw.get("qty")) or Decimal("0"),
            notes=str(raw.get("notes", "")),
            raw=dict(raw),
        )
        results.append(event)

    return results
