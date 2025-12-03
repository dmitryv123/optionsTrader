from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, Iterable, List, Optional, Tuple

from django.utils import timezone

from accounts.models import Client
from portfolio.models import Instrument, IbkrContract, Portfolio
from strategies.models import (
    StrategyInstance,
    Signal,
    Opportunity,
)


# ---------------------------------------------------------------------------
# Canonical signal types & payload conventions (T0054.2)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class SignalType:
    """
    Simple namespace for canonical signal type strings.

    This is not enforced at the DB level, but gives us a single place to
    document and re-use the types across strategies.
    """
    name: str
    description: str
    payload_hint: Dict[str, str]


CANONICAL_SIGNALS: Dict[str, SignalType] = {
    # Example: summarizing current profit capture / PL state
    "profit_capture_status": SignalType(
        name="profit_capture_status",
        description="Summarizes realized/unrealized PL and whether targets were hit.",
        payload_hint={
            "realized_pl": "Decimal or float, total realized PL for the scope investigated.",
            "unrealized_pl": "Decimal or float, current unrealized PL.",
            "target_reached": "bool, whether profit target is met.",
        },
    ),

    # Example: metrics for a candidate option trade (used by scanners)
    "candidate_ror": SignalType(
        name="candidate_ror",
        description="Metrics for a candidate trade: return on risk, margin usage, etc.",
        payload_hint={
            "ror_pct": "float, % return on risk for the candidate.",
            "margin_required": "Decimal or float, margin needed.",
            "dte": "int, days to expiry.",
            "delta": "float, option delta.",
        },
    ),

    # Example: internal risk or health flags
    "risk_limit_hit": SignalType(
        name="risk_limit_hit",
        description="Raised when a risk limit is breached (e.g., margin utilization).",
        payload_hint={
            "limit_name": "str, symbolic name of the risk limit.",
            "current_value": "float, current metric value.",
            "threshold": "float, configured limit.",
        },
    ),
}


# ---------------------------------------------------------------------------
# Signals helper (T0054.1, T0054.3)
# ---------------------------------------------------------------------------

def record_signals(
    *,
    strategy_instance: StrategyInstance,
    asof_ts: Optional[datetime] = None,
    portfolio: Optional[Portfolio] = None,
    underlier: Optional[Instrument] = None,
    ibkr_con: Optional[IbkrContract] = None,
    signals: Iterable[Tuple[str, Dict[str, Any]]],
) -> List[Signal]:
    """
    Persist a batch of signals for a given StrategyInstance.

    Parameters
    ----------
    strategy_instance:
        StrategyInstance emitting the signals.
    asof_ts:
        Timestamp of the snapshot/decision; defaults to now() if None.
    portfolio:
        Optional explicit portfolio; defaults to strategy_instance.portfolio.
    underlier:
        Optional Instrument related to these signals.
    ibkr_con:
        Optional IbkrContract related to these signals.
    signals:
        Iterable of (signal_type, payload_dict).

    Returns
    -------
    List[Signal]
        The created Signal rows.
    """
    if asof_ts is None:
        asof_ts = timezone.now()
    if timezone.is_naive(asof_ts):
        asof_ts = timezone.make_aware(asof_ts, timezone.get_current_timezone())

    client: Client = strategy_instance.client
    if portfolio is None:
        portfolio = strategy_instance.portfolio

    created: List[Signal] = []

    for sig_type, payload in signals:
        # Ensure payload is at least a dict
        if payload is None:
            payload = {}

        obj = Signal.objects.create(
            client=client,
            strategy_instance=strategy_instance,
            asof_ts=asof_ts,
            portfolio=portfolio,
            underlier=underlier,
            ibkr_con=ibkr_con,
            type=sig_type,
            payload=payload,
        )
        created.append(obj)

    return created


# ---------------------------------------------------------------------------
# Opportunities helper (T0055.1–T0055.3)
# ---------------------------------------------------------------------------

# Normalized metric keys (T0055.2)
OPPORTUNITY_METRIC_KEYS = ["ror_pct", "iv_rank", "delta", "dte", "risk"]


def _normalize_metrics(raw_metrics: Dict[str, Any]) -> Dict[str, Any]:
    """
    Normalize core opportunity metrics into a consistent shape.

    We:
      - Copy through 'ror_pct', 'iv_rank', 'delta', 'dte', 'risk' if present
      - Leave all additional keys intact
    """
    if raw_metrics is None:
        raw_metrics = {}

    metrics: Dict[str, Any] = dict(raw_metrics)  # copy

    # Ensure keys are present in a consistent format if provided
    # (We don't force them to exist; we only normalize what's there.)
    for key in OPPORTUNITY_METRIC_KEYS:
        if key in metrics:
            continue
        # We don't invent values here; absence is acceptable.
        # This preserves flexibility across strategies.

    return metrics


def record_opportunities(
    *,
    client: Client,
    asof_ts: Optional[datetime],
    underlier: Instrument,
    ibkr_con: Optional[IbkrContract],
    opportunity_specs: Iterable[Dict[str, Any]],
    required_margin_default: Optional[Decimal] = None,
    notes_default: str = "",
) -> List[Opportunity]:
    """
    Persist a batch of Opportunity rows for a single (underlier, contract).

    Parameters
    ----------
    client:
        Owning client/tenant.
    asof_ts:
        Timestamp associated with these opportunities; defaults to now() if None.
    underlier:
        The underlying Instrument for which these opportunities were evaluated.
    ibkr_con:
        Optional specific option/contract.
    opportunity_specs:
        Iterable of dicts with keys:
          - 'metrics' (dict)      : required
          - 'required_margin'     : optional, Decimal/float
          - 'notes'               : optional, str
    required_margin_default:
        If an item does not specify 'required_margin', this default is used.
    notes_default:
        Default notes if none provided.

    Returns
    -------
    List[Opportunity]
        The created Opportunity rows.
    """
    if asof_ts is None:
        asof_ts = timezone.now()
    if timezone.is_naive(asof_ts):
        asof_ts = timezone.make_aware(asof_ts, timezone.get_current_timezone())

    created: List[Opportunity] = []

    for spec in opportunity_specs:
        raw_metrics = spec.get("metrics") or {}
        metrics = _normalize_metrics(raw_metrics)

        required_margin_val = spec.get("required_margin", required_margin_default)
        if required_margin_val is not None and not isinstance(required_margin_val, Decimal):
            required_margin_val = Decimal(str(required_margin_val))

        notes_val = spec.get("notes", notes_default or "")

        obj = Opportunity.objects.create(
            client=client,
            asof_ts=asof_ts,
            underlier=underlier,
            ibkr_con=ibkr_con,
            metrics=metrics,
            required_margin=required_margin_val,
            notes=notes_val,
        )
        created.append(obj)

    return created
