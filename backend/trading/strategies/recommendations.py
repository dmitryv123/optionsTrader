from __future__ import annotations

import uuid
from dataclasses import asdict
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.utils import timezone

from accounts.models import Client, BrokerAccount
from portfolio.models import Instrument, IbkrContract, Portfolio
from strategies.models import (
    StrategyInstance,
    StrategyVersion,
    Recommendation,
)
from trading.strategies.base import PlannedAction


# ---------------------------------------------------------------------------
# Canonical action vocabulary (T0056.2)
# ---------------------------------------------------------------------------


class RecommendationActions:
    """
    Canonical set of recommended action strings for Recommendation.action.

    These are not enforced at the DB level, but they give us a single place
    to standardize names across strategies.
    """

    # Wheel-style core actions
    SELL_PUT = "sell_put"
    BUY_STOCK = "buy_stock"
    SELL_CALL = "sell_call"
    CLOSE_PUT = "close_put"
    CLOSE_CALL = "close_call"
    CLOSE_STOCK = "close_stock"

    # Rolls / adjustments
    ROLL_PUT = "roll_put"
    ROLL_CALL = "roll_call"
    ROLL_STOCK = "roll_stock"

    # Generic / fallback actions
    OPEN_LONG = "open_long"
    OPEN_SHORT = "open_short"
    CLOSE_POSITION = "close_position"
    ADJUST_HEDGE = "adjust_hedge"
    DIAGNOSTIC = "diagnostic"  # e.g., Wheel v1 stub

    # For convenience
    ALL = {
        SELL_PUT,
        BUY_STOCK,
        SELL_CALL,
        CLOSE_PUT,
        CLOSE_CALL,
        CLOSE_STOCK,
        ROLL_PUT,
        ROLL_CALL,
        ROLL_STOCK,
        OPEN_LONG,
        OPEN_SHORT,
        CLOSE_POSITION,
        ADJUST_HEDGE,
        DIAGNOSTIC,
    }


def normalize_action_name(action: str) -> str:
    """
    Normalize Recommendation.action strings (T0056.2).

    - Lowercases
    - Trims whitespace
    - If result matches one of our canonical names, returns it
    - Otherwise returns the normalized string as-is (we don't hard-fail)
    """
    if not action:
        return action

    norm = action.strip().lower()
    # Allow users to pass things like "Sell Put" or "SELL_PUT" etc.
    norm = norm.replace(" ", "_")

    if norm in RecommendationActions.ALL:
        return norm

    # Not a known canonical string — we still return a normalized name,
    # but it's outside the curated vocabulary.
    return norm


# ---------------------------------------------------------------------------
# record_recommendations helper (T0056.1, T0056.3, T0056.4)
# ---------------------------------------------------------------------------


def record_recommendations(
    *,
    strategy_instance: StrategyInstance,
    strategy_version: StrategyVersion,
    client: Client,
    portfolio: Optional[Portfolio],
    broker_account: Optional[BrokerAccount],
    asof_ts,
    planned_actions: Iterable[PlannedAction],
) -> List[Recommendation]:
    """
    Persist a batch of PlannedActions as Recommendation rows for a given
    StrategyInstance / StrategyVersion (T0056.1–T0056.4).

    This helper *enforces* consistent population of all key fields:

      - client
      - strategy_instance
      - strategy_version
      - portfolio
      - broker_account
      - underlier (Instrument)  [from PlannedAction.underlier]
      - ibkr_con (IbkrContract) [from PlannedAction.ibkr_con]
      - action (normalized string)
      - params (dict)
      - confidence (Decimal)
      - rationale (str)
      - plan_id (UUID or None)

    It also supports multi-step plans by propagating PlannedAction.plan_id
    to Recommendation.plan_id (T0056.4).
    """
    if asof_ts is None:
        asof_ts = timezone.now()
    if timezone.is_naive(asof_ts):
        asof_ts = timezone.make_aware(asof_ts, timezone.get_current_timezone())

    created: List[Recommendation] = []

    for act in planned_actions:
        # PlannedAction is our internal dataclass; we assume it has at least:
        #   - underlier: Optional[Instrument]
        #   - ibkr_con: Optional[IbkrContract]
        #   - action: str
        #   - params: Dict[str, Any]
        #   - confidence: Decimal
        #   - rationale: str
        #   - plan_id: Optional[uuid.UUID]
        underlier: Optional[Instrument] = getattr(act, "underlier", None)
        ibkr_con: Optional[IbkrContract] = getattr(act, "ibkr_con", None)
        action_raw: str = getattr(act, "action", "")
        params: Dict[str, Any] = getattr(act, "params", {}) or {}
        confidence_val = getattr(act, "confidence", Decimal("0"))
        rationale_val = getattr(act, "rationale", "") or ""
        plan_id_val = getattr(act, "plan_id", None)

        # Normalize action string (T0056.2)
        action_norm = normalize_action_name(action_raw)

        # Ensure confidence is a Decimal
        if not isinstance(confidence_val, Decimal):
            confidence_val = Decimal(str(confidence_val))

        # plan_id semantics (T0056.4)
        # If present on the PlannedAction, use it as-is; if it's a string,
        # try to coerce to UUID. If absent, keep None (single-step rec).
        if isinstance(plan_id_val, str):
            try:
                plan_id_val = uuid.UUID(plan_id_val)
            except Exception:
                # Keep as string if coercion fails; better not to throw away
                # user-supplied grouping information.
                pass

        rec = Recommendation.objects.create(
            client=client,
            portfolio=portfolio,
            broker_account=broker_account,
            strategy_instance=strategy_instance,
            strategy_version=strategy_version,
            asof_ts=asof_ts,
            underlier=underlier,
            ibkr_con=ibkr_con,
            action=action_norm,
            params=params,
            confidence=confidence_val,
            rationale=rationale_val,
            plan_id=plan_id_val,
        )
        created.append(rec)

    return created


# ---------------------------------------------------------------------------
# Execution-plan view builder (T0057.1–T0057.2)
# ---------------------------------------------------------------------------


def build_execution_plan_view(
    recommendations: Iterable[Recommendation],
) -> Dict[str, Any]:
    """
    Build a read-only execution plan view from Recommendation rows.

    - Groups recommendations by plan_id (T0057.1)
      * plan_id is used as the "execution plan" identifier
      * Recommendations with plan_id == None are treated as their own
        single-item plans

    - Within each plan, sorts recommendations by:
        1) confidence DESC
        2) action name ASC
        3) asof_ts ASC
      (T0057.2 — simple, deterministic priority ordering)

    The returned structure is plain JSON-serializable data (dicts/lists),
    suitable for feeding a REST API or UI layer.
    """
    # 1) Group by plan_id (None => its own "singleton" plan)
    grouped: Dict[str, List[Recommendation]] = {}

    for rec in recommendations:
        key = str(rec.plan_id) if rec.plan_id is not None else f"singleton:{rec.id}"
        grouped.setdefault(key, []).append(rec)

    plans: List[Dict[str, Any]] = []

    for plan_key, recs in grouped.items():
        # 2) Sort within the plan
        recs_sorted = sorted(
            recs,
            key=lambda r: (
                -(r.confidence or Decimal("0")),
                r.action or "",
                r.asof_ts,
            ),
        )

        # 3) Convert to JSON-friendly payload
        plan_items: List[Dict[str, Any]] = []
        max_conf = Decimal("0")

        for r in recs_sorted:
            confidence_val = r.confidence or Decimal("0")
            if confidence_val > max_conf:
                max_conf = confidence_val

            plan_items.append(
                {
                    "id": str(r.id),
                    "asof_ts": r.asof_ts.isoformat(),
                    "action": r.action,
                    "confidence": float(confidence_val),
                    "rationale": r.rationale,
                    "underlier": getattr(r.underlier, "symbol", None),
                    "ibkr_con_id": getattr(r.ibkr_con, "con_id", None),
                    "params": r.params,
                    "plan_id": str(r.plan_id) if r.plan_id else None,
                }
            )

        plans.append(
            {
                "plan_key": plan_key,  # internal grouping key
                "plan_id": (
                    str(recs_sorted[0].plan_id) if recs_sorted[0].plan_id else None
                ),
                "max_confidence": float(max_conf),
                "num_steps": len(plan_items),
                "items": plan_items,
            }
        )

    # 4) Sort plans themselves by max_confidence DESC, then plan_key
    plans_sorted = sorted(
        plans,
        key=lambda p: (-Decimal(str(p["max_confidence"])), p["plan_key"]),
    )

    return {
        "plans": plans_sorted,
        "total_plans": len(plans_sorted),
        "total_recommendations": sum(len(p["items"]) for p in plans_sorted),
    }
