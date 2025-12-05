from __future__ import annotations

from dataclasses import asdict
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

from django.utils import timezone

from strategies.models import StrategyInstance, StrategyRun
from trading.strategies.executor import run_strategy_instance
from trading.strategies.recommendations import build_execution_plan_view
from trading.strategies.signals import CANONICAL_SIGNALS
from strategies.models import Signal, Opportunity, Recommendation


def _ensure_aware(dt: Optional[datetime]) -> datetime:
    if dt is None:
        dt = timezone.now()
    if timezone.is_naive(dt):
        dt = timezone.make_aware(dt, timezone.get_current_timezone())
    return dt


def run_all_enabled_strategies(
    *,
    asof_ts: Optional[datetime] = None,
    strategy_slug: Optional[str] = None,
    dry_run: bool = False,
) -> List[Dict[str, Any]]:
    """
    Run all enabled StrategyInstances (optionally filtered by strategy slug).

    T0058.1  — Implement run_all_enabled_strategies(asof_ts=None)
    T0058.2  — For each StrategyInstance, create StrategyRun and call engine
    T0058.3  — Log per-run summary (signals, opportunities, recommendations)

    Returns a list of per-strategy summary dicts:
      {
        "instance_id": <uuid>,
        "client": "...",
        "name": "...",
        "status": "ok" | "error",
        "num_actions": N,
        "num_signals": S,
        "num_opportunities": O,
        "num_recommendations": R,
      }
    """
    asof_ts = _ensure_aware(asof_ts)

    qs = StrategyInstance.objects.filter(enabled=True)
    if strategy_slug:
        qs = qs.filter(strategy_version__strategy_def__slug=strategy_slug)

    summaries: List[Dict[str, Any]] = []

    for instance in qs.select_related("client", "strategy_version", "portfolio"):
        # Call the engine. It already creates StrategyRun rows.
        actions = run_strategy_instance(
            instance,
            asof_ts=asof_ts,
            persist_recommendations=not dry_run,
        )

        # Per-run summary based on DB counts *after* the run
        num_signals = Signal.objects.filter(strategy_instance=instance, asof_ts__gte=asof_ts).count()
        num_opps = Opportunity.objects.filter(strategy_instance=instance, asof_ts__gte=asof_ts).count()
        num_recs = Recommendation.objects.filter(strategy_instance=instance, asof_ts__gte=asof_ts).count()

        # We take the latest StrategyRun for this instance at/after asof_ts
        last_run = (
            StrategyRun.objects.filter(strategy_instance=instance, run_ts__gte=asof_ts)
            .order_by("-run_ts")
            .first()
        )

        summaries.append(
            {
                "instance_id": str(instance.id),
                "client": instance.client.name,
                "name": instance.name,
                "strategy": instance.strategy_version.strategy_def.slug,
                "status": last_run.status if last_run else "unknown",
                "num_actions": len(actions),
                "num_signals": num_signals,
                "num_opportunities": num_opps,
                "num_recommendations": num_recs,
                "dry_run": dry_run,
            }
        )

    return summaries
