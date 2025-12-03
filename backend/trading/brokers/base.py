# trading/brokers/base.py

from __future__ import annotations
from typing import Protocol, Iterable, runtime_checkable

from .types import (
    AccountSnapshotData,
    PositionData,
    OrderData,
    ExecutionData,
    OptionEventData,
)



@runtime_checkable
class BrokerAPI(Protocol):
    """
    Abstract broker interface.

    Any concrete broker connector (IBKR, SIM, other brokers) must implement
    this Protocol. The rest of the system (ingestion, risk engine, strategies)
    should only depend on BrokerAPI and the normalized datatypes from
    trading.brokers.types, never on vendor-specific SDKs or payloads.

    Implementations (e.g., IBKRClient) must provide read-only
    access to account state, positions, and trade-related data.

    This interface is intentionally broker-agnostic and uses
    normalized dataclasses from trading.brokers.types.

    This keeps the system portable and testable.
    """

    def fetch_account_snapshots(self) -> Iterable[AccountSnapshotData]:
        """
        Retrieve one or more account snapshots from the broker.

        Returns:
            An iterable of AccountSnapshotData objects. In many setups this
            will be exactly one snapshot per broker account, but the interface
            allows multiple results for flexibility (e.g., multi-subaccount
            connectors or future features).

        Implementations should:
        - Normalize all numeric values to Decimal
        - Provide a realistic asof_ts per snapshot
        - Preserve any extra fields in the `extras` dict
        """
        ...

    def fetch_positions(self) -> Iterable[PositionData]:
        """
        Retrieve all currently open positions for the underlying broker account.

        Returns:
            An iterable of PositionData instances, one per position (symbol /
            contract) as reported by the broker at the time of the call.

        Implementations should:
        - Normalize quantities, costs, and prices to Decimal
        - Ensure asof_ts represents the broker's view of "now" or the
          timestamp when the snapshot was obtained
        - Preserve the raw broker payload in the `raw` dict for debugging
        """
        ...

# --- EPIC 3: orders / executions / option events ---

    def fetch_open_orders(self) -> Iterable[OrderData]:
        """
        Return the currently open (working) orders for the account(s).

        This may also include recently completed or cancelled orders
        depending on the broker API, but consumer code should treat this
        as the best-effort "current order book" view.
        """
        ...

    def fetch_executions(self) -> Iterable[ExecutionData]:
        """
        Return recent executions (fills) in normalized form.

        The exact lookback window is broker-dependent, but ingestion
        must be idempotent: re-ingesting the same executions should
        not create duplicates in the database.
        """
        ...

    def fetch_option_events(self) -> Iterable[OptionEventData]:
        """
        Return option lifecycle events such as assignments, exercises,
        and expirations, normalized into OptionEventData objects.
        """
        ...