from django.shortcuts import render

# Create your views here.

# strategies/views.py
from collections import defaultdict
from django.utils import timezone
from rest_framework.decorators import api_view
from rest_framework.response import Response

from strategies.models import Recommendation
from accounts.models import AccountSnapshot

@api_view(["GET"])
def recommendations_today(request):
    # define "today" in UTC (simple & robust for now)
    today = timezone.now().date()

    # pull today's recs; select related to avoid N+1
    recs = (
        Recommendation.objects
        .select_related(
            "portfolio", "broker_account",
            "underlier", "opportunity",
            "strategy_instance", "strategy_version",
        )
        .filter(asof_ts__date=today)
        .order_by("asof_ts")
    )

    # group by plan (fall back to each rec's own id if plan_id is null)
    plans = defaultdict(list)
    for r in recs:
        key = str(r.plan_id or r.id)
        plans[key].append(r)

    # attach latest account snapshot per broker account
    latest_snapshots = {}
    for r in recs:
        ba_id = r.broker_account_id
        if ba_id and ba_id not in latest_snapshots:
            snap = (
                AccountSnapshot.objects
                .filter(broker_account_id=ba_id)
                .order_by("-asof_ts")
                .first()
            )
            if snap:
                latest_snapshots[ba_id] = {
                    "asof_ts": snap.asof_ts.isoformat(),
                    "currency": snap.currency,
                    "cash": str(snap.cash),
                    "buying_power": str(snap.buying_power),
                    "maintenance_margin": str(snap.maintenance_margin),
                    "used_margin": str(snap.used_margin),
                }

    # shape response
    out = []
    for plan_id, items in plans.items():
        # common context pulled from the first rec in the plan
        first = items[0]
        opp = first.opportunity
        out.append({
            "plan_id": plan_id,
            "client_id": str(first.client_id),
            "portfolio": {
                "id": str(first.portfolio_id),
                "name": first.portfolio.name,
            },
            "broker_account": {
                "id": str(first.broker_account_id),
                "nickname": first.broker_account.nickname if first.broker_account else None,
                "latest_snapshot": latest_snapshots.get(first.broker_account_id),
            },
            "asof_ts": first.asof_ts.isoformat(),
            "opportunity": (
                {
                    "id": str(opp.id),
                    "underlier": first.underlier.symbol,
                    "metrics": opp.metrics,
                    "required_margin": str(opp.required_margin) if opp.required_margin is not None else None,
                } if opp else None
            ),
            "recommendations": [
                {
                    "id": str(r.id),
                    "action": r.action,
                    "underlier": r.underlier.symbol,
                    "ibkr_con_id": r.ibkr_con_id,
                    "params": r.params,
                    "confidence": float(r.confidence),
                    "rationale": r.rationale,
                    "strategy": {
                        "instance": str(r.strategy_instance_id),
                        "version": str(r.strategy_version_id),
                    },
                }
                for r in items
            ],
        })

    return Response({"date": today.isoformat(), "plans": out})
