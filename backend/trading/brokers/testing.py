# trading/brokers/testing.py

from __future__ import annotations

#from datetime import datetime, timezone
from datetime import datetime, timezone as dt_timezone  # stdlib UTC, if you need it
from django.utils import timezone
from decimal import Decimal
from typing import Iterable, List

from trading.brokers.base import BrokerAPI
from trading.brokers.types import (
    AccountSnapshotData,
    PositionData,
    OrderData,
    ExecutionData,
    OptionEventData, )


class FakeBrokerAPI(BrokerAPI):
    """
    Simple in-memory broker implementation for tests.

    You can pre-load it with snapshot and position data and then
    use it to test ingestion without touching real IBKR.
    """

    def __init__(
            self,
            # account_code: str,
            account_snapshots: Iterable[AccountSnapshotData] | None = None,
            positions: Iterable[PositionData] | None = None,
            orders: list[OrderData] | None = None,
            executions: list[ExecutionData] | None = None,
            option_events: list[OptionEventData] | None = None,
    ):
        # self._account_code = account_code
        self.account_snapshots: List[AccountSnapshotData] = list(account_snapshots or [])
        self.positions: List[PositionData] = list(positions or [])
        self.orders = orders or []
        self.executions = executions or []
        self.option_events = option_events or []

    def fetch_account_snapshots(self) -> Iterable[AccountSnapshotData]:
        return list(self.account_snapshots)

    def fetch_positions(self) -> Iterable[PositionData]:
        return list(self.positions)

    # --- EPIC 3: orders / executions / option events ---

    def fetch_open_orders(self) -> Iterable[OrderData]:
        """
            Return whatever orders list was injected into this fake instance.
            """
        return list(self.orders)

    def fetch_executions(self) -> Iterable[ExecutionData]:
        """
            Return whatever executions list was injected into this fake instance.
            """
        return list(self.executions)

    def fetch_option_events(self) -> Iterable[OptionEventData]:
        """
            Return whatever option_events list was injected into this fake instance.
            """
        return list(self.option_events)


def make_simple_fake_account_snapshot(
        broker_account_code: str = "U1234567",
        currency: str = "USD",
) -> AccountSnapshotData:
    """
    Convenience helper: build a single AccountSnapshotData with simple values.
    """
    now = timezone.now() # datetime.now(timezone.utc)
    return AccountSnapshotData(
        broker_account_code=broker_account_code,
        currency=currency,
        asof_ts=now,
        cash=Decimal("100000"),
        buying_power=Decimal("300000"),
        maintenance_margin=Decimal("50000"),
        used_margin=Decimal("10000"),
        extras={"source": "fake"},
    )


def make_simple_fake_position(
        broker_account_code: str = "U1234567",
        symbol: str = "AAPL",
) -> PositionData:
    """
    Convenience helper: build a simple PositionData for tests.
    """
    now = timezone.now() # datetime.now(timezone.utc)
    return PositionData(
        broker_account_code=broker_account_code,
        symbol=symbol,
        exchange="NASDAQ",
        asset_type="equity",
        currency="USD",
        con_id=265598,
        qty=Decimal("10"),
        avg_cost=Decimal("150.25"),
        market_price=Decimal("170.00"),
        market_value=Decimal("1700.00"),
        asof_ts=now,
        raw={"source": "fake"},
    )
