from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Iterable, List, Tuple

from trading.strategies.base import PlannedAction


@dataclass
class SafetyLimits:
    """
    Soft safety constraints for strategy output (Story 4.6).

    These are meant to be read from StrategyInstance.config["safety"], e.g.:

      "safety": {
        "max_recommendations": 10,
        "max_per_plan": 4,
        "max_total_notional": 200000,
      }
    """
    max_recommendations: int = 50
    max_per_plan: int = 10
    max_total_notional: Decimal = Decimal("1e9")  # effectively unlimited by default


def apply_safety_limits(
    actions: Iterable[PlannedAction],
    limits: SafetyLimits,
) -> Tuple[List[PlannedAction], dict]:
    """
    Apply simple safety rules to a list of PlannedAction objects:

      - Cap total number of actions (max_recommendations)
      - Cap actions per plan_id (max_per_plan)
      - (Placeholder) rough check on total notional if `notional` exists in params

    Returns (filtered_actions, stats_dict).
    """
    actions = list(actions)

    # Group by plan_id (None => its own group)
    grouped = {}
    for act in actions:
        key = getattr(act, "plan_id", None) or f"singleton:{id(act)}"
        grouped.setdefault(key, []).append(act)

    filtered: List[PlannedAction] = []
    total_notional = Decimal("0")

    for group_key, group_actions in grouped.items():
        # Limit per-plan
        limited_group = group_actions[: limits.max_per_plan]
        for act in limited_group:
            # Optional: accumulate 'notional' if present in params (best-effort)
            notional = act.params.get("notional") if hasattr(act, "params") else None
            if notional is not None:
                try:
                    total_notional += Decimal(str(notional))
                except Exception:
                    pass
            filtered.append(act)

    # Global max_recommendations cap
    filtered = filtered[: limits.max_recommendations]

    stats = {
        "original_count": len(actions),
        "grouped_plans": len(grouped),
        "filtered_count": len(filtered),
        "max_recommendations": limits.max_recommendations,
        "max_per_plan": limits.max_per_plan,
        "total_notional": str(total_notional),
    }

    return filtered, stats
