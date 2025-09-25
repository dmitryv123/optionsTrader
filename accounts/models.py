
# Create your models here.

from django.conf import settings
from django.db import models
from django.utils.translation import gettext_lazy as _
# from .common import TimeUUIDModel  # if you externalize it
from django.db.models import JSONField
from decimal import Decimal

# ----- paste the TimeUUIDModel here if not sharing it from a common module -----
import uuid

class TimeUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    class Meta:
        abstract = True
# -------------------------------------------------------------------------------

class Client(TimeUUIDModel):
    name = models.CharField(max_length=128, unique=True)
    is_active = models.BooleanField(default=True)
    settings = JSONField(default=dict, blank=True)

    def __str__(self):
        return self.name

class ClientMembership(TimeUUIDModel):
    class Role(models.TextChoices):
        OWNER = "owner", _("Owner")
        MANAGER = "manager", _("Manager")
        TRADER = "trader", _("Trader")
        VIEWER = "viewer", _("Viewer")

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="client_memberships")
    role = models.CharField(max_length=16, choices=Role.choices, default=Role.VIEWER)

    class Meta:
        unique_together = [("client", "user")]
        indexes = [
            models.Index(fields=["client", "user"]),
            models.Index(fields=["user"]),
        ]

    def __str__(self):
        return f"{self.user} @ {self.client} ({self.role})"


class BrokerAccount(TimeUUIDModel):
    class Kind(models.TextChoices):
            LIVE = "IBKR", "IBKR Live"
            PAPER_LINKED = "IBKR-PAPER", "IBKR Paper (via IBKR)"
            SIMULATED = "SIM", "Simulated (local)"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="broker_accounts")
    kind = models.CharField(max_length=16, choices=Kind.choices, default=Kind.LIVE)
    account_code = models.CharField(max_length=64, blank=True, default="")  # empty for SIM
    base_currency = models.CharField(max_length=8, default="USD")
    nickname = models.CharField(max_length=64, blank=True, default="")
    metadata = JSONField(default=dict, blank=True)  # fee model, routing prefs, etc.

    class Meta:
        unique_together = [("client", "kind", "account_code")]
        indexes = [
            models.Index(fields=["client", "kind"]),
            models.Index(fields=["client", "account_code"]),
        ]

    def __str__(self):
        return f"{self.account_code} ({self.broker})"


# class BrokerAccount(TimeUUIDModel):
#     def __str__(self):
#         return f"{self.account_code} ({self.broker})"


class AccountSnapshot(TimeUUIDModel):
    """
        Point-in-time broker account snapshot for capital/margin-aware decisions and audits.
    """

    client = models.ForeignKey('accounts.Client', on_delete=models.CASCADE, related_name='account_snapshots')
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, related_name='snapshots')
    asof_ts = models.DateTimeField()
    currency = models.CharField(max_length=8, default="USD")

    cash = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))
    buying_power = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))
    maintenance_margin = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))
    used_margin = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))
    extras = JSONField(default=dict, blank=True)  # any broker-specific fields


    class Meta:
        indexes = [
            models.Index(fields=['client', 'broker_account', 'asof_ts']),
            models.Index(fields=['broker_account', 'asof_ts']),
        ]

        constraints = [
            models.UniqueConstraint(fields=['broker_account', 'asof_ts'], name='uniq_broker_asof')
        ]


    def __str__(self):
        return f"{self.broker_account.account_code} @ {self.asof_ts:%Y-%m-%d %H:%M:%S}"


