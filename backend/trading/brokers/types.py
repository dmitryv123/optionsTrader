# trading/brokers/types.py

from __future__ import annotations
from dataclasses import dataclass
from decimal import Decimal
from datetime import datetime
from typing import Optional, Dict, Any


# ---------------------------------------------------------------------------
# NORMALIZED TYPES
#
# These represent broker-agnostic, cleaned, well-typed data structures used
# throughout the ingestion layer. Every broker integration (IBKR, SIM, etc.)
# must return these types — never raw broker payloads.
# ---------------------------------------------------------------------------


@dataclass
class AccountSnapshotData:
    """
    Normalized account-level snapshot from any broker.

    This is the canonical structure used by ingestion to create
    AccountSnapshot model instances. Broker-specific fields should be placed
    into `extras` so the system can remain vendor-agnostic.
    """
    broker_account_code: str         # Ex: "U1234567"
    currency: str                    # Ex: "USD"
    asof_ts: datetime                # Timestamp at broker or ingestion time

    cash: Decimal                    # Net cash
    buying_power: Decimal            # Effective BP according to broker
    maintenance_margin: Decimal      # Maintenance margin requirement
    used_margin: Decimal             # Margin already consumed

    extras: Dict[str, Any]           # Raw/extra broker fields


@dataclass
class PositionData:
    """
    Normalized representation of a single open position.

    This structure is consumed by the positions ingestion pipeline and
    mapped into Position, Instrument, and IbkrContract tables.

    All numeric fields must be Decimal-converted before instantiation.
    `raw` should hold any broker-native payload for debugging.
    """
    broker_account_code: str         # Broker account owning this position
    symbol: str                      # Ex: "AAPL"
    exchange: Optional[str]          # Ex: "NASDAQ", sometimes None
    asset_type: str                  # "equity", "option", "etf", etc.
    currency: str                    # Usually "USD"

    con_id: Optional[int]            # Broker contract ID if available (IBKR)
    qty: Decimal                     # Number of shares/contracts
    avg_cost: Decimal                # Average cost per share/contract
    market_price: Decimal            # Current market price per unit
    market_value: Decimal            # Full market value = qty * market_price

    asof_ts: datetime                # Timestamp when broker reported the data
    raw: Dict[str, Any]              # Raw broker payload for audit/debugging
