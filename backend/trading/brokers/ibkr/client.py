# trading/brokers/ibkr/client.py

from __future__ import annotations
from typing import Iterable, List

from accounts.models import BrokerAccount
from trading.brokers.base import BrokerAPI
from trading.brokers.types import (AccountSnapshotData,
                                   PositionData,
                                   OrderData,
                                   ExecutionData,
                                   OptionEventData)

from trading.brokers.exceptions import BrokerConnectionError
from trading.brokers.ibkr.config import IBKRConnectionConfig, get_ibkr_connection_config
from trading.brokers.ibkr.transport import IBKRTransport
from trading.brokers.ibkr.mappers import (map_raw_account_to_snapshot,
                                          map_raw_positions,
                                          map_raw_orders,
                                          map_raw_executions,
                                          map_raw_option_events, )


class IBKRClient(BrokerAPI):
    """
    Concrete BrokerAPI implementation for Interactive Brokers (IBKR).

    Responsibilities:
      - Own an IBKRTransport instance (connection/session lifecycle)
      - Fetch raw payloads via transport
      - Map them into normalized dataclasses using mappers
      - Never expose vendor-specific SDK objects to the rest of the system

    This class is instantiated via `from_broker_account` by the broker registry.
    """

    def __init__(self, broker_account: BrokerAccount, config: IBKRConnectionConfig):
        self.broker_account = broker_account
        self.cfg = config
        self.transport = IBKRTransport(config)

    # ------------------------------------------------------------------
    # Factory constructor
    # ------------------------------------------------------------------
    @classmethod
    def from_broker_account(cls, broker_account: BrokerAccount) -> "IBKRClient":
        """
        Create an IBKRClient for a given BrokerAccount.

        Uses get_ibkr_connection_config() to obtain connection settings,
        so different environments can configure IBKR via Django settings
        or environment variables without changing code.
        """
        cfg = get_ibkr_connection_config()
        return cls(broker_account=broker_account, config=cfg)

    # ------------------------------------------------------------------
    # BrokerAPI implementation
    # ------------------------------------------------------------------
    def fetch_account_snapshots(self) -> Iterable[AccountSnapshotData]:
        """
        Fetch normalized account snapshot(s) from IBKR for this BrokerAccount.

        For now we assume a 1:1 mapping: one BrokerAccount maps to one IBKR
        account code, so this returns a single-element list. The interface
        remains Iterable[...] to allow flexibility later.
        """
        self.transport.connect()
        try:
            raw = self.transport.fetch_raw_account_data(self.broker_account.account_code)
            snapshot = map_raw_account_to_snapshot(raw, self.broker_account.account_code)
            return [snapshot]
        finally:
            self.transport.disconnect()

    def fetch_positions(self) -> Iterable[PositionData]:
        """
        Fetch normalized open positions from IBKR for this BrokerAccount.
        """
        self.transport.connect()
        try:
            raw_positions = self.transport.fetch_raw_positions(self.broker_account.account_code)
            positions: List[PositionData] = map_raw_positions(raw_positions, self.broker_account.account_code)
            return positions
        finally:
            self.transport.disconnect()

    # ------------------------------------------------------------------
    # EPIC 3: orders / executions / option events
    # ------------------------------------------------------------------

    def fetch_open_orders(self) -> Iterable[OrderData]:
        """
        Fetch open (and possibly recently completed) orders for this account
        and map them into normalized OrderData objects.
        """
        # In a real implementation, you might handle connect/disconnect here.
        # For now we assume the transport manages its own lifecycle or is
        # already connected.

        # DV-> following pattern above handle connect/disconnect

        self.transport.connect()
        try:
            raw_orders = self.transport.fetch_raw_open_orders(self.broker_account.account_code)
            return map_raw_orders(raw_orders, self.broker_account.account_code)
        finally:
            self.transport.disconnect()

    def fetch_executions(self) -> Iterable[ExecutionData]:
        """
        Fetch recent executions (fills) for this account and map them into
        normalized ExecutionData objects.
        """
        self.transport.connect()
        try:
            raw_execs = self.transport.fetch_raw_executions(self.broker_account.account_code)
            return map_raw_executions(raw_execs, self.broker_account.account_code)
        finally:
            self.transport.disconnect()

    def fetch_option_events(self) -> Iterable[OptionEventData]:
        """
        Fetch option lifecycle events (assignments / exercises / expirations)
        for this account and map them into normalized OptionEventData objects.
        """
        self.transport.connect()
        try:
            raw_events = self._transport.fetch_raw_option_events(self.broker_account.account_code)
            return map_raw_option_events(raw_events, self.broker_account.account_code)
        finally:
            self.transport.disconnect()
