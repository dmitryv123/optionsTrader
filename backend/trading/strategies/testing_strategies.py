# trading/strategies/testing_strategies.py
from __future__ import annotations

from decimal import Decimal
from typing import List

from trading.strategies.base import BaseStrategy, StrategyContext, PlannedAction


class DummyNoopStrategy(BaseStrategy):
    """A simple test strategy that emits a single no-op planned action."""

    def run(self, context: StrategyContext) -> List[PlannedAction]:
        return [
            PlannedAction(
                underlier=None,
                action="noop",
                params={"msg": "test"},
                confidence=Decimal("100"),
                rationale="Dummy test strategy",
            )
        ]
