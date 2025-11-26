# Create your models here.

from decimal import Decimal
import uuid
from django.db import models
from django.db.models import JSONField
from django.utils.translation import gettext_lazy as _
from accounts.models import Client
from portfolio.models import Portfolio, Instrument, IbkrContract
from accounts.models import BrokerAccount

# Base (local for now)
class TimeUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# ---------------------------------------------------------------------------
# Strategy catalogue: Definition (name/slug) and Version (schema + code_ref)
# ---------------------------------------------------------------------------
class StrategyDefinition(TimeUUIDModel):
    name = models.CharField(max_length=128, unique=True)  # e.g., "Wheel"
    slug = models.SlugField(max_length=64, unique=True)  # e.g., "wheel"
    description = models.TextField(blank=True, default="")

    def __str__(self):
        return f"{self.name}"


class StrategyVersion(TimeUUIDModel):
    strategy_def = models.ForeignKey(StrategyDefinition, on_delete=models.CASCADE, related_name="versions")
    version = models.CharField(max_length=64, default="v1")  # e.g., "v1", "2025-09"
    schema = JSONField(default=dict, blank=True)  # JSON Schema for config validation (optional)
    code_ref = models.CharField(max_length=256, blank=True, default="")  # dotted path / plugin id

    class Meta:
        unique_together = [("strategy_def", "version")]
        indexes = [
            models.Index(fields=["strategy_def", "version"]),
        ]

    def __str__(self):
        return f"{self.strategy_def.slug}@{self.version}"


# ---------------------------------------------------------------------------
# StrategyInstance = formerly "Policy": tenant/portfolio-bound instance
# ---------------------------------------------------------------------------
class StrategyInstance(TimeUUIDModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="strategy_instances")
    name = models.CharField(max_length=128)  # Instance label visible to user
    strategy_version = models.ForeignKey(StrategyVersion, on_delete=models.PROTECT, related_name="instances")
    portfolio = models.ForeignKey(Portfolio, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="strategy_instances")
    enabled = models.BooleanField(default=True)
    tags = models.CharField(max_length=256, blank=True, default="")
    config = JSONField(default=dict, blank=True)  # Validated against StrategyVersion.schema out-of-band

    class Meta:
        unique_together = [("client", "name")]
        indexes = [
            models.Index(fields=["client", "portfolio"]),
            models.Index(fields=["client", "enabled"]),
        ]

    def __str__(self):
        return f"{self.client}:{self.name} ({self.strategy_version})"


# ---------------------------------------------------------------------------
# Runs & Signals (generic, strategy-agnostic)
# ---------------------------------------------------------------------------
class StrategyRun(TimeUUIDModel):
    class Mode(models.TextChoices):
        DAILY = "daily", _("Daily")
        BACKTEST = "backtest", _("Backtest")
        MANUAL = "manual", _("Manual")

    strategy_instance = models.ForeignKey(StrategyInstance, on_delete=models.CASCADE, related_name="runs")
    run_ts = models.DateTimeField()
    mode = models.CharField(max_length=16, choices=Mode.choices, default=Mode.DAILY)
    status = models.CharField(max_length=32, default="ok")
    stats = JSONField(default=dict, blank=True)
    errors = JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["strategy_instance", "run_ts"]),
        ]


class Signal(TimeUUIDModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="signals")
    strategy_instance = models.ForeignKey(StrategyInstance, on_delete=models.CASCADE, related_name="signals")
    asof_ts = models.DateTimeField()
    portfolio = models.ForeignKey(Portfolio, on_delete=models.SET_NULL, null=True, blank=True, related_name="signals")
    underlier = models.ForeignKey(Instrument, on_delete=models.SET_NULL, null=True, blank=True,
                                  related_name="signals_underlier")
    ibkr_con = models.ForeignKey(IbkrContract, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="signals_contract")

    type = models.CharField(max_length=64)  # e.g., "profit_capture_status", "candidate_ror"
    payload = JSONField(default=dict, blank=True)  # arbitrary metrics

    class Meta:
        indexes = [
            models.Index(fields=["client", "asof_ts"]),
            models.Index(fields=["client", "type"]),
        ]


# ---------------------------------------------------------------------------
# Opportunity (scanner-produced candidate with ranked metrics)
# ---------------------------------------------------------------------------
class Opportunity(TimeUUIDModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="opportunities")
    asof_ts = models.DateTimeField()
    underlier = models.ForeignKey(Instrument, on_delete=models.PROTECT, related_name="opportunities_underlier")
    ibkr_con = models.ForeignKey(IbkrContract, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="opportunities_contract")
    metrics = JSONField(default=dict,
                        blank=True)  # e.g., {"ror_pct":1.2,"iv_rank":34,"risk":0.55,"delta":-0.25,"dte":14}
    required_margin = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["client", "asof_ts"]),
            models.Index(fields=["client"]),
        ]

    def __str__(self):
        return f"Opp:{self.underlier.symbol} @ {self.asof_ts:%Y-%m-%d %H:%M}"


# ---------------------------------------------------------------------------
# Recommendations (generic action + params + optional plan bundling)
# ---------------------------------------------------------------------------
class Recommendation(TimeUUIDModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="recommendations")
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="recommendations")
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, related_name="recommendations")

    #strategy_instance = models.ForeignKey(StrategyInstance, on_delete=models.PROTECT, related_name="recommendations", default=Decimal("0"))
    strategy_instance = models.ForeignKey(
        StrategyInstance,
        on_delete=models.PROTECT,
        related_name="recommendations",
    )
    # denormalize the version actually used at emission time (audit/reproducibility)
    # strategy_version = models.ForeignKey(StrategyVersion, on_delete=models.PROTECT, related_name="recommendations", default=" ")
    strategy_version = models.ForeignKey(
        StrategyVersion,
        on_delete=models.PROTECT,
        related_name="recommendations",
        null=True,
        blank=True,
    )

    asof_ts = models.DateTimeField()
    underlier = models.ForeignKey(Instrument, on_delete=models.PROTECT, related_name="recommendations_underlier")
    ibkr_con = models.ForeignKey(IbkrContract, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="recommendations_contract")

    # action is free-form string (keeps schema stable across strategies)
    action = models.CharField(max_length=64)  # e.g., "sell_put", "close", "roll", "open_long"
    params = JSONField(default=dict, blank=True)  # e.g., {"strike": 180, "expiry": "...", "qty": 1, "limit_price": 2.5}

    confidence = models.DecimalField(max_digits=5, decimal_places=2, default=Decimal("0"))  # 0-100
    rationale = models.TextField(blank=True, default="")

    # optional bundle identifier to group multi-step plans (e.g., close + open)
    plan_id = models.UUIDField(null=True, blank=True)

    # optional direct link to a persisted Opportunity (still okay to also carry id in params)
    opportunity = models.ForeignKey(Opportunity, on_delete=models.SET_NULL, null=True, blank=True,
                                    related_name="recommendations")

    class Meta:
        indexes = [
            models.Index(fields=["client", "asof_ts"]),
            models.Index(fields=["client", "portfolio", "asof_ts"]),
            models.Index(fields=["client", "action"]),
            models.Index(fields=["plan_id"]),
            models.Index(fields=["opportunity"]),
        ]
