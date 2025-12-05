# backend/trading/strategies/execution_intents.py

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional
from uuid import UUID


@dataclass
class ExecutionIntent:
    """
    Broker-agnostic execution intent produced from a PlannedAction.

    This is the object that the ExecutionRouter will consume. It is intentionally
    simple and uses primitives only (no Django models) so it can be easily logged,
    tested, and serialized if needed.

    - broker_account_code: which account this order should be sent from
    - con_id: IBKR contract identifier (or None for non-IB instruments in future)
    - side: 'BUY' or 'SELL'
    - order_type: 'MKT', 'LMT', etc.
    - quantity: number of contracts/shares
    - limit_price: optional limit price for LMT / STP-LMT
    - tif: 'DAY', 'GTC', ...
    - action: original PlannedAction.action string
    - plan_id: bundle identifier for multi-leg plans (rolls, spreads, etc.)
    - notes: human-readable rationale
    - raw_params: original params from PlannedAction for debugging/audit
    """

    broker_account_code: str
    con_id: Optional[int]
    side: str  # 'BUY' or 'SELL'
    order_type: str  # 'MKT', 'LMT', etc.
    quantity: Decimal
    limit_price: Optional[Decimal] = None
    tif: str = "DAY"

    action: str = ""
    plan_id: Optional[UUID] = None
    notes: str = ""
    raw_params: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        # Normalize side / order_type / tif to upper-case for consistency
        if self.side:
            self.side = self.side.upper()
        if self.order_type:
            self.order_type = self.order_type.upper()
        if self.tif:
            self.tif = self.tif.upper()
