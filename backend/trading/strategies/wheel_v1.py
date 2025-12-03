# trading/strategies/wheel_v1.py
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional

from portfolio.models import Instrument
from trading.strategies.base import BaseStrategy, StrategyContext, PlannedAction


class WheelStrategy(BaseStrategy):
    """
    Minimal v1 stub for the Wheel strategy.

    This implementation is deliberately simple:
      - It inspects the context (positions, cash, buying power)
      - Emits a single PlannedAction of type "diagnostic" describing state
      - Does NOT select strikes / expiries / send real trade instructions yet

    Later stories (scanner + ranking + production rules) will turn this into
    a "real" wheel.
    """

    def run(self, context: StrategyContext) -> List[PlannedAction]:
        # Strategy config (already validated by schema, but we keep it defensive)
        cfg = self.config or {}
        universe = cfg.get("underlying_universe", [])

        # For now, we just report basic account + position state.
        summary = {
            "universe": universe,
            "cash": str(context.cash),
            "buying_power": str(context.buying_power),
            "maintenance_margin": str(context.maintenance_margin),
            "used_margin": str(context.used_margin),
            "num_positions": len(context.positions),
            "num_open_orders": len(context.open_orders),
        }

        return [
            PlannedAction(
                underlier=None,  # no specific symbol yet
                action="diagnostic",
                params={
                    "strategy": self.slug,
                    "instance": self.name,
                    "summary": summary,
                },
                confidence=Decimal("0"),
                rationale="WheelStrategy v1 diagnostic only (no live trades).",
            )
        ]
