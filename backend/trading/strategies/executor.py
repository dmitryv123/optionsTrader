# trading/strategies/executor.py
from __future__ import annotations

from datetime import datetime, timedelta
from decimal import Decimal
from typing import List, Optional, Tuple

from django.utils import timezone

from accounts.models import AccountSnapshot
from portfolio.models import Position, Order, Execution
from strategies.models import StrategyInstance, Recommendation, StrategyVersion
from trading.strategies.base import StrategyContext, PlannedAction, BaseStrategy
from trading.strategies.registry import get_registered_strategy


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
    version: StrategyVersion = instance.strategy_version
    registered = get_registered_strategy(version)

    impl = registered.callable

    # We support either:
    #   - a class derived from BaseStrategy (preferred)
    #   - a callable(context, instance) -> list[PlannedAction]
    if isinstance(impl, type) and issubclass(impl, BaseStrategy):
        strategy_obj = impl(instance)
        context = build_strategy_context(instance, asof_ts=asof_ts)
        actions = strategy_obj.run(context)
    else:
        # Fallback: treat impl as a simple function
        context = build_strategy_context(instance, asof_ts=asof_ts)
        actions = impl(context=context, instance=instance)  # type: ignore[call-arg]

    actions = actions or []

    if persist_recommendations and actions:
        _persist_recommendations_from_actions(instance, context, actions)

    return actions


def _persist_recommendations_from_actions(
    instance: StrategyInstance,
    context: StrategyContext,
    actions: List[PlannedAction],
) -> List[Recommendation]:
    """
    Turn PlannedAction objects into Recommendation rows.

    This is a simple v1 mapping and can be refined in later stories (e.g.,
    adding richer plan grouping, multi-leg handling, etc.).
    """
    version = instance.strategy_version
    portfolio = context.portfolio
    broker_account = context.broker_account

    created: List[Recommendation] = []

    for action in actions:
        rec = Recommendation.objects.create(
            client=instance.client,
            portfolio=portfolio,
            broker_account=broker_account,
            strategy_instance=instance,
            strategy_version=version,
            asof_ts=context.asof_ts,
            underlier=action.underlier,
            ibkr_con=None,  # can be populated by later stages
            action=action.action,
            params=action.params,
            confidence=action.confidence,
            rationale=action.rationale,
            plan_id=None,
            opportunity=None,
        )
        created.append(rec)

    return created
