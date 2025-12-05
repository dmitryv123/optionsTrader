# trading/strategies/executor.py
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from django.utils import timezone

from accounts.models import AccountSnapshot
from portfolio.models import Position, Order, Execution
from strategies.models import StrategyInstance, Recommendation, StrategyVersion, StrategyRun
from trading.strategies.base import StrategyContext, PlannedAction, BaseStrategy
from trading.strategies.registry import get_registered_strategy
from trading.strategies.recommendations import record_recommendations
from trading.strategies.safety import SafetyLimits, apply_safety_limits

import logging
import time
import traceback

logger = logging.getLogger(__name__)


def _get_effective_asof_ts(asof_ts: Optional[datetime] = None) -> datetime:
    if asof_ts is not None:
        if timezone.is_naive(asof_ts):
            asof_ts = timezone.make_aware(asof_ts, timezone.get_current_timezone())
        return asof_ts
    return timezone.now()


def build_strategy_context(
        instance: StrategyInstance,
        asof_ts: Optional[datetime] = None,
) -> StrategyContext:
    """
    Build a StrategyContext for a given StrategyInstance at a given point in time.

    This function is intentionally conservative: it only pulls the core data the
    strategy engine v1 needs:
      - latest AccountSnapshot
      - all current Positions for the portfolio
      - open Orders for the broker account
      - recent Executions (e.g., last 7 days)
    """
    asof_ts = _get_effective_asof_ts(asof_ts)

    version = instance.strategy_version
    client = instance.client
    portfolio = instance.portfolio
    if portfolio is None:
        raise ValueError(f"StrategyInstance {instance.id} has no portfolio set")

    broker_account = portfolio.broker_account
    if broker_account is None:
        raise ValueError(f"Portfolio {portfolio.id} has no broker_account set")

    # Latest account snapshot for this broker account
    snapshot = (
        AccountSnapshot.objects.filter(broker_account=broker_account)
            .order_by("-asof_ts")
            .first()
    )
    # print("snapshot.cash", snapshot.cash)

    if snapshot is None:
        # No snapshot yet: treat as zeroed account (safe default for dry runs/backtests)
        cash = Decimal("0")
        buying_power = Decimal("0")
        maintenance_margin = Decimal("0")
        used_margin = Decimal("0")
    else:
        cash = snapshot.cash
        buying_power = snapshot.buying_power
        maintenance_margin = snapshot.maintenance_margin
        used_margin = snapshot.used_margin

    # All positions for this portfolio as of now
    positions = list(
        Position.objects.filter(
            portfolio=portfolio,
            broker_account=broker_account,
        )
    )

    # Open orders for this broker account
    open_orders = list(
        Order.objects.filter(
            broker_account=broker_account,
        ).exclude(status__in=["Filled", "Cancelled"])
    )

    # Executions in the last 7 days
    recent_cutoff = asof_ts - timedelta(days=7)
    recent_executions = list(
        Execution.objects.filter(
            client=client,
            fill_ts__gte=recent_cutoff,
        )
    )

    return StrategyContext(
        client=client,
        portfolio=portfolio,
        broker_account=broker_account,
        asof_ts=asof_ts,
        cash=cash,
        buying_power=buying_power,
        maintenance_margin=maintenance_margin,
        used_margin=used_margin,
        positions=positions,
        open_orders=open_orders,
        recent_executions=recent_executions,
        config=instance.config or {},
        extras={},
    )


def run_strategy_instance(
        instance: StrategyInstance,
        asof_ts: Optional[datetime] = None,
        persist_recommendations: bool = False,
) -> List[PlannedAction]:
    """
    High-level orchestrator:

      1) Load the registered strategy implementation for the instance.version
      2) Build a StrategyContext
      3) Invoke strategy.run(context) -> list[PlannedAction]
      4) Optionally persist as Recommendation rows

    Returns the list of PlannedAction objects regardless of persistence.
    """

    start = time.time()

    if asof_ts is None:
        asof_ts = timezone.now()
    if timezone.is_naive(asof_ts):
        asof_ts = timezone.make_aware(asof_ts, timezone.get_current_timezone())

    version: StrategyVersion = instance.strategy_version
    registered = get_registered_strategy(version)

    impl = registered.callable

    # We support either:
    #   - a class derived from BaseStrategy (preferred)
    #   - a callable(context, instance) -> list[PlannedAction]
    run = StrategyRun.objects.create(
        strategy_instance=instance,
        run_ts=asof_ts,
        mode=StrategyRun.Mode.MANUAL,
        status="in_progress",
        stats={},
        errors={},
        debug_log=[],
    )

    def log(msg: str, **extra):
        entry = {"msg": msg, **extra}
        # Append to in-DB debug log
        run.debug_log.append(entry)
        # Also send to Python logger
        logger.info(f"[StrategyRun {run.id}] {msg}", extra=extra)

    try:
        if isinstance(impl, type) and issubclass(impl, BaseStrategy):
            strategy_obj = impl(instance)
            log("build_context_start")
            context = build_strategy_context(instance, asof_ts=asof_ts)
            log(
                "build_context_done",
                cash=str(context.cash),
                buying_power=str(context.buying_power),
                maintenance_margin=str(context.maintenance_margin),
                used_margin=str(context.used_margin),
                num_positions=len(context.positions),
                num_open_orders=len(context.open_orders),
            )
            log("strategy_execute_start", strategy=instance.strategy_version.code_ref)
            actions = strategy_obj.run(context)
            log("strategy_execute_done", num_actions=len(actions))

            # Optional safety layer, controlled by instance.config
            safety_cfg = (instance.config or {}).get("safety") or {}
            limits = SafetyLimits(
                max_recommendations=safety_cfg.get("max_recommendations", 50),
                max_per_plan=safety_cfg.get("max_per_plan", 10),
                max_total_notional=Decimal(str(safety_cfg.get("max_total_notional", "1e9"))),
            )
            # print("safety_cfg",safety_cfg,"actions",actions,"limits",limits)
            actions_after_safety, safety_stats = apply_safety_limits(actions, limits)
            # print("safetyactions_after_safety_cfg", actions_after_safety, "safety_stats", safety_stats)
            log("safety_applied", **safety_stats)

        else:
            # Fallback: treat impl as a simple function
            log("impl_build_context_start")
            context = build_strategy_context(instance, asof_ts=asof_ts)
            log(
                "impl_build_context_done",
                cash=str(context.cash),
                buying_power=str(context.buying_power),
                maintenance_margin=str(context.maintenance_margin),
                used_margin=str(context.used_margin),
                num_positions=len(context.positions),
                num_open_orders=len(context.open_orders),
            )
            log("impl_execute_start", strategy=instance.strategy_version.code_ref)
            actions = impl(context=context, instance=instance)  # type: ignore[call-arg]
            actions_after_safety = actions
            log("impl_execute_done", num_actions=len(actions))

        actions = actions or []
        actions_after_safety = actions_after_safety or []

        # Use actions_after_safety from here on if you want strict safety
        effective_actions = actions_after_safety # actions
        # when ready replace actions with actions_after_safety if safety limits
        # to be strictly applied. Safety config lives in StrategyInstance.config["safety"]

        if persist_recommendations and effective_actions:
            log("persist_recommendations_start", num_actions=len(effective_actions))
            record_recommendations(
                strategy_instance=instance,
                strategy_version=instance.strategy_version,
                client=instance.client,
                portfolio=context.portfolio,
                broker_account=context.broker_account,
                asof_ts=context.asof_ts,
                planned_actions=effective_actions,
            )
            log("persist_recommendations_done")
            # _persist_recommendations_from_actions(instance, context, actions)
        duration_ms = int((time.time() - start) * 1000)
        run.duration_ms = duration_ms
        run.status = "ok"
        run.stats = {"num_actions": len(actions)}
        run.save(update_fields=["status", "stats", "duration_ms", "debug_log"])

        return actions

    except Exception as exc:
        tb = traceback.format_exc()
        log("error", error=str(exc))
        run.status = "error"
        run.error_trace = tb
        run.errors = {"message": str(exc)}
        duration_ms = int((time.time() - start) * 1000)
        run.duration_ms = duration_ms
        run.save(update_fields=["status", "errors", "error_trace", "duration_ms", "debug_log"])
        raise

# def _persist_recommendations_from_actions(
#     instance: StrategyInstance,
#     context: StrategyContext,
#     actions: List[PlannedAction],
# ) -> List[Recommendation]:
#     """
#     Turn PlannedAction objects into Recommendation rows.
#
#     This is a simple v1 mapping and can be refined in later stories (e.g.,
#     adding richer plan grouping, multi-leg handling, etc.).
#     """
#     version = instance.strategy_version
#     portfolio = context.portfolio
#     broker_account = context.broker_account
#
#     created: List[Recommendation] = []
#
#     for action in actions:
#         rec = Recommendation.objects.create(
#             client=instance.client,
#             portfolio=portfolio,
#             broker_account=broker_account,
#             strategy_instance=instance,
#             strategy_version=version,
#             asof_ts=context.asof_ts,
#             underlier=action.underlier,
#             ibkr_con=None,  # can be populated by later stages
#             action=action.action,
#             params=action.params,
#             confidence=action.confidence,
#             rationale=action.rationale,
#             plan_id=None,
#             opportunity=None,
#         )
#         created.append(rec)
#
#     return created
