# backend/trading/strategies/execution_mapping.py

from __future__ import annotations

from dataclasses import asdict
from decimal import Decimal
from typing import Dict, Iterable, List

from trading.strategies.execution_intents import ExecutionIntent
from trading.strategies.base import PlannedAction  # where your PlannedAction dataclass lives


class ExecutionMappingError(ValueError):
    """
    Raised when we cannot map a PlannedAction into a valid ExecutionIntent.
    """


# Minimal set of "order-producing" actions for now.
# Others (like 'diagnostic') are explicitly rejected as non-executable.
EXECUTABLE_ACTIONS = {
    "sell_put",
    "sell_call",
    "buy_to_close",
    "sell_to_close",
    "buy_shares",
    "sell_shares",
}


def _extract_decimal(params: Dict, *keys: str, required: bool = False) -> Decimal:
    """
    Helper to pull a Decimal from params under one of the given keys.
    If required=True and no key is found or value is falsy, raises ExecutionMappingError.
    """
    for key in keys:
        if key in params and params[key] not in (None, ""):
            return Decimal(str(params[key]))
    if required:
        raise ExecutionMappingError(f"Missing required numeric parameter; tried keys={keys!r}")
    return Decimal("0")


def map_planned_action_to_execution_intent(
    action: PlannedAction,
    context,
) -> ExecutionIntent:
    """
    Map a single PlannedAction into an ExecutionIntent.

    `context` is expected to expose at least:
      - context.broker_account.account_code

    We don't type-enforce StrategyContext here; anything duck-typed with a
    `broker_account` that has `account_code` is acceptable. This keeps the
    mapping layer decoupled and easy to test.

    Raises ExecutionMappingError for:
      - non-executable action types (e.g., 'diagnostic')
      - missing quantity
      - missing con_id (no contract to trade)
      - inability to infer side/order_type
    """
    # 1) Only certain actions correspond to real orders at this stage.
    if action.action not in EXECUTABLE_ACTIONS:
        raise ExecutionMappingError(f"Non-executable or unsupported action: {action.action!r}")

    if not getattr(context, "broker_account", None) or not context.broker_account.account_code:
        raise ExecutionMappingError("Strategy context is missing broker_account.account_code")

    params: Dict = action.params or {}

    # 2) Quantity is required for any actual order
    quantity = _extract_decimal(params, "qty", "quantity", required=True)
    if quantity <= 0:
        raise ExecutionMappingError("ExecutionIntent requires positive quantity")

    # 3) Determine limit price if present, otherwise None
    limit_price = None
    if "limit_price" in params and params["limit_price"] not in (None, ""):
        limit_price = Decimal(str(params["limit_price"]))

    # 4) Determine order_type
    order_type = params.get("order_type")
    if not order_type:
        # Default heuristic: if limit_price is present, use LMT, otherwise MKT
        order_type = "LMT" if limit_price is not None else "MKT"

    # 5) Time-in-force
    tif = (params.get("tif") or "DAY").upper()

    # 6) con_id: prefer action.ibkr_con, fallback to explicit con_id in params
    con_id = None
    if getattr(action, "ibkr_con", None) is not None:
        con_id = getattr(action.ibkr_con, "con_id", None)
    if con_id is None:
        raw_con_id = params.get("con_id")
        if raw_con_id is not None:
            con_id = int(raw_con_id)

    if con_id is None:
        raise ExecutionMappingError("Executable actions must carry an ibkr_con or con_id")

    # 7) Side mapping based on action.action
    side_map = {
        "sell_put": "SELL",
        "sell_call": "SELL",
        "sell_shares": "SELL",
        "sell_to_close": "SELL",
        "buy_to_close": "BUY",
        "buy_shares": "BUY",
    }
    side = side_map.get(action.action)
    if not side:
        raise ExecutionMappingError(f"Could not determine side from action: {action.action!r}")

    intent = ExecutionIntent(
        broker_account_code=context.broker_account.account_code,
        con_id=con_id,
        side=side,
        order_type=order_type,
        quantity=quantity,
        limit_price=limit_price,
        tif=tif,
        action=action.action,
        plan_id=action.plan_id,
        notes=action.rationale or "",
        raw_params=dict(params),
    )
    return intent


def map_actions_to_intents(actions: Iterable[PlannedAction], context) -> List[ExecutionIntent]:
    """
    Convenience helper: map a collection of PlannedAction objects to a list of ExecutionIntent.
    Any non-executable actions will raise ExecutionMappingError, so the caller can decide
    whether to catch and skip, or fail the whole batch.
    """
    return [map_planned_action_to_execution_intent(a, context) for a in actions]
