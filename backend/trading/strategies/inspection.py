from __future__ import annotations

from typing import Iterable

from strategies.models import StrategyRun, StrategyInstance, Recommendation, Signal


def get_last_runs(strategy_instance_id, limit: int = 10):
    return (
        StrategyRun.objects
        .filter(strategy_instance_id=strategy_instance_id)
        .order_by("-run_ts")[:limit]
    )


def get_last_recommendations(strategy_instance_id, limit: int = 20):
    return (
        Recommendation.objects
        .filter(strategy_instance_id=strategy_instance_id)
        .order_by("-asof_ts")[:limit]
    )


def get_last_signals(strategy_instance_id, limit: int = 20):
    return (
        Signal.objects
        .filter(strategy_instance_id=strategy_instance_id)
        .order_by("-asof_ts")[:limit]
    )
