# trading/brokers/ibkr/transport.py

from __future__ import annotations
from typing import Any, Iterable, Optional, List

from trading.brokers.ibkr.config import IBKRConnectionConfig
from trading.brokers.exceptions import BrokerConnectionError


class IBKRTransport:
    """
    Thin wrapper around actual IBKR connectivity.

    It isolates external dependencies (ib_insync or Client Portal REST API)
    behind a minimal interface. This ensures:

      - No vendor SDK leaks beyond this module
      - Testability (can easily mock IBKRTransport)
      - Ability to replace connectivity implementation without touching
        upstream logic (client, mappers, ingestion)

    NOTE: Implementation is intentionally minimal for T0029.
    Real logic (ib_insync / REST calls) will be added in EPIC 3.
    """

    def __init__(self, config: IBKRConnectionConfig):
        self.cfg = config
        self.connected: bool = False
        self._session: Optional[Any] = None  # Placeholder for real client

    # ------------------------------------------------------------------
    # Connection lifecycle
    # ------------------------------------------------------------------
    def connect(self) -> None:
        """
        Establish a connection to IBKR Gateway or TWS.

        For T0029, this is a stub. Later:
          - If using ib_insync: IB().connect(...)
          - If using Client Portal API: create HTTPS session

        Must raise BrokerConnectionError on failure.
        """
        try:
            # Stub logic — replace with real connection later
            self.connected = True
            self._session = object()  # placeholder for real client/session
        except Exception as e:
            raise BrokerConnectionError(f"Failed to connect: {e}") from e

    def disconnect(self) -> None:
        """
        Close the IBKR connection / HTTP session.
        """
        # Stub logic
        self.connected = False
        self._session = None

    # ------------------------------------------------------------------
    # Raw data fetchers — MUST be implemented in EPIC 3
    # ------------------------------------------------------------------
    def fetch_raw_account_data(self, account_code: str) -> Any:
        """
        Fetch raw account-level snapshot from IBKR.

        For T0029: return a stub dict.

        Later implementations will:
          - call ib_insync's accountSummary()
          - or call Client Portal REST endpoint /v1/api/portfolio/<account>/summary
        """
        # print('fetch_raw_account_data')
        # print('self.connected',self.connected)
        if not self.connected:
            raise BrokerConnectionError("Not connected to IBKR transport")

        # Temporary stub payload
        return {
            "account_code": account_code,
            "currency": "USD",
            "cash": "100000",
            "buying_power": "300000",
            "maintenance_margin": "50000",
            "used_margin": "10000",
            "timestamp": None,  # will be replaced by real value
        }

    def fetch_raw_positions(self, account_code: str) -> Iterable[Any]:
        """
        Fetch raw open positions from IBKR.

        For T0029: return a stub list of dicts.

        Later implementation will map to:
          - ib_insync's positions()
          - or REST endpoint /v1/api/portfolio/<account>/positions
        """
        if not self.connected:
            raise BrokerConnectionError("Not connected to IBKR transport")

        # Temporary stub raw response
        return [
            {
                "symbol": "AAPL",
                "exchange": "NASDAQ",
                "asset_type": "equity",
                "currency": "USD",
                "con_id": 265598,          # example IBKR contract ID
                "qty": "10",
                "avg_cost": "150.25",
                "market_price": "170.00",
                "market_value": "1700.00",
                "timestamp": None,
            }
        ]
    # ------------------------------------------------------------------
    # EPIC 3: raw trade / event APIs (stubs for now)
    # ------------------------------------------------------------------

    def fetch_raw_open_orders(self, account_code: str) -> Any:
        """
        Fetch raw open orders for a given account from IBKR.

        For now this is a stub. In EPIC 5 we will wire this to the actual
        IBKR API (e.g. ib_insync or native API). The ingestion layer will
        not depend on the exact raw shape; it will only use the
        ibkr.mappers.map_raw_orders(...) function.
        """
        # TODO: implement real call to IBKR in a later epic.
        # For now, return an empty list or raise NotImplementedError.
        return []

    def fetch_raw_executions(self, account_code: str) -> Any:
        """
        Fetch raw executions (fills) for a given account from IBKR.

        Stub implementation for now; wired to real API later.
        """
        return []

    def fetch_raw_option_events(self, account_code: str) -> Any:
        """
        Fetch raw option lifecycle events (assignment/exercise/expiration)
        for a given account from IBKR.

        Stub implementation for now; wired to real API later.
        """
        return []

