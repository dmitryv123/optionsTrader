# trading/brokers/base.py

from __future__ import annotations
from typing import Protocol, Iterable, runtime_checkable

from .types import AccountSnapshotData, PositionData


@runtime_checkable
class BrokerAPI(Protocol):
    """
    Abstract broker interface.

    Any concrete broker connector (IBKR, SIM, other brokers) must implement
    this Protocol. The rest of the system (ingestion, risk engine, strategies)
    should only depend on BrokerAPI and the normalized datatypes from
    trading.brokers.types, never on vendor-specific SDKs or payloads.

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
