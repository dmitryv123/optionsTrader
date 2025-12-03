# trading/strategies/base.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.utils import timezone

from accounts.models import Client, BrokerAccount, AccountSnapshot
from portfolio.models import Portfolio, Position, Order, Execution, Instrument
from strategies.models import StrategyInstance


@dataclass
class StrategyContext:
    """
    Snapshot of everything a strategy needs to decide what to do *right now*.
    This is deliberately read-only with respect to trading decisions.
    """

    client: Client
    portfolio: Portfolio
    broker_account: BrokerAccount

    asof_ts: datetime

    # Account-level info
    cash: Decimal
    buying_power: Decimal
    maintenance_margin: Decimal
    used_margin: Decimal

    # Positions, orders, executions (already filtered for this portfolio/account)
    positions: List[Position] = field(default_factory=list)
    open_orders: List[Order] = field(default_factory=list)
    recent_executions: List[Execution] = field(default_factory=list)

    # Strategy-specific:
    config: Dict[str, Any] = field(default_factory=dict)
    extras: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlannedAction:
    """
    Generic, strategy-agnostic "thing to do".

    This is what strategies emit. A separate layer (Story 4.3+) will be
    responsible for turning PlannedActions into Recommendation rows and then,
    optionally, into actual broker orders.
    """

    underlier: Optional[Instrument]
    action: str  # e.g. "sell_put", "buy_to_close", "roll", "open_collar"
    params: Dict[str, Any] = field(default_factory=dict)

    confidence: Decimal = Decimal("0")
    rationale: str = ""
    plan_id: Optional[str] = None  # can be used to group multi-leg plans


class BaseStrategy:
    """
    Base class all strategy implementations should extend.

    Minimal contract:
      - Accept a StrategyInstance at init time
      - Implement `run(context)` and return a list[PlannedAction]
    """

    def __init__(self, instance: StrategyInstance):
        self.instance = instance
        self.client = instance.client
        self.version = instance.strategy_version
        self.definition = self.version.strategy_def
        self.config: Dict[str, Any] = instance.config or {}

    @property
    def slug(self) -> str:
        return self.definition.slug

    @property
    def name(self) -> str:
        return self.instance.name

    def run(self, context: StrategyContext) -> List[PlannedAction]:
        """
        Main entrypoint for decision making.

        Subclasses MUST override this and return a list of PlannedAction
        objects. The base implementation does nothing.
        """
        return []
