# trading/strategies/wheel_v1.py
from __future__ import annotations

from decimal import Decimal
from typing import List, Optional, Dict , Any
import logging
from portfolio.models import Instrument
from trading.strategies.base import BaseStrategy, StrategyContext, PlannedAction

logger = logging.getLogger(__name__)


def _dec_to_str(value: Decimal) -> str:
    """
    Render Decimal to a minimal, human-friendly string:
      100000.000000 -> "100000"
      100000.120000 -> "100000.12"
    """
    s = format(value, "f")  # fixed-point, no exponent
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


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

    def evaluate(self, context: StrategyContext) -> Dict[str, Any]: # Actually , this method not in use, later on we can deal with it if needed
        """
        T0053.1 — Implement WheelStrategy.evaluate(context) -> dict skeleton
        T0053.2 — Stub logic to produce in-memory signals/opportunities/recommendations
        T0053.3 — Add debug logging hooks inside WheelStrategy.
        """
        # --- Risk / safety guard: if no effective cash or buying power, do nothing ---
        if context.buying_power <= 0 or context.cash <= 0:
            logger.info(
                "WheelStrategy: no actions due to zero/negative cash or buying power "
                "(cash=%s, bp=%s)",
                context.cash,
                context.buying_power,
            )
            return []

        cfg = self.instance.config or {}

        logger.info(
            "WheelStrategy.evaluate instance=%s client=%s portfolio=%s asof=%s",
            self.instance.id,
            context.client.name,
            context.portfolio.name,
            context.asof_ts,
        )
        logger.debug("WheelStrategy config: %r", cfg)
        logger.debug(
            "Account state: cash=%s buying_power=%s used_margin=%s positions=%d open_orders=%d",
            context.cash,
            context.buying_power,
            context.used_margin,
            len(context.positions),
            len(context.open_orders),
        )

        # Skeleton only: we don't yet implement the full wheel logic.
        # We just prepare the structures so that later logic can append items.
        signals: List[Dict[str, Any]] = []
        opportunities: List[Dict[str, Any]] = []
        recommendations: List[Dict[str, Any]] = []

        # Example debug hook: list underliers we care about
        underliers = cfg.get("underliers", [])
        logger.debug("WheelStrategy underliers from config: %s", underliers)

        # TODO (future): populate signals/opportunities based on context and config.
        logger.debug(
            "WheelStrategy result summary: signals=%d opportunities=%d recommendations=%d",
            len(signals),
            len(opportunities),
            len(recommendations),
        )

        return {
            "signals": signals,
            "opportunities": opportunities,
            "recommendations": recommendations,
            "actions": [],  # engine can later derive actions from recs
        }

    def run(self, context: StrategyContext) -> List[PlannedAction]:
        # Strategy config (already validated by schema, but we keep it defensive)

        # --- Risk / safety guard: if no effective cash or buying power, do nothing ---
        if context.buying_power <= 0 or context.cash <= 0:
            logger.info(
                "WheelStrategy: no actions due to zero/negative cash or buying power "
                "(cash=%s, bp=%s)",
                context.cash,
                context.buying_power,
            )
            return []
        cfg = self.config or {}
        universe = cfg.get("underlying_universe", [])

        # For now, we just report basic account + position state.
        summary = {
            "universe": universe,
            "cash": _dec_to_str(context.cash),
            "buying_power": _dec_to_str(context.buying_power),
            "maintenance_margin": _dec_to_str(context.maintenance_margin),
            "used_margin": _dec_to_str(context.used_margin),
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
