# Create your models here.

from django.db import models
from django.db.models import JSONField
from decimal import Decimal
# from common import TimeUUIDModel
import uuid


class TimeUUIDModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


# FK to Client and BrokerAccount from accounts app
from accounts.models import Client, BrokerAccount


class Instrument(TimeUUIDModel):
    class AssetType(models.TextChoices):
        EQUITY = "equity", "Equity"
        ETF = "etf", "ETF"
        OPTION = "option", "Option"
        FUTURE = "future", "Future"
        CRYPTO = "crypto", "Crypto"
        FX = "fx", "FX"

    symbol = models.CharField(max_length=32)  # AAPL, SPY
    name = models.CharField(max_length=128, blank=True, default="")
    exchange = models.CharField(max_length=32, blank=True, default="")
    asset_type = models.CharField(max_length=16, choices=AssetType.choices)
    currency = models.CharField(max_length=8, default="USD")
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = [("symbol", "exchange", "asset_type", "currency")]
        indexes = [
            models.Index(fields=["symbol", "asset_type"]),
        ]

    # def __str__(self):
    #     return f"{self.symbol} ({self.asset_type})"

    def __str__(self):
        return f"{self.symbol} [{self.get_asset_type_display()}]"


class IbkrContract(TimeUUIDModel):
    # Stable IB identifier
    con_id = models.BigIntegerField(unique=True)
    instrument = models.ForeignKey(Instrument, on_delete=models.CASCADE, related_name="ibkr_contracts")
    sec_type = models.CharField(max_length=16)  # STK, OPT, etc.
    exchange = models.CharField(max_length=32, blank=True, default="")
    currency = models.CharField(max_length=8, default="USD")
    local_symbol = models.CharField(max_length=64, blank=True, default="")
    last_trade_date_or_contract_month = models.CharField(max_length=16, blank=True, default="")  # e.g., 20250920
    strike = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    right = models.CharField(max_length=1, blank=True, default="")  # C/P or blank for stocks
    multiplier = models.IntegerField(null=True, blank=True)  # 100 for options typically
    metadata = JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["con_id"]),
            models.Index(fields=["instrument"]),
        ]

    def __str__(self):
        return f"{self.con_id} / {self.local_symbol}"


class Portfolio(TimeUUIDModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="portfolios")
    name = models.CharField(max_length=128)
    base_currency = models.CharField(max_length=8, default="USD")
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.SET_NULL, null=True, blank=True,
                                       related_name="portfolios")
    metadata = JSONField(default=dict, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['client', 'broker_account', 'name'],
                name='uniq_portfolio_client_ba_name'
            )
        ]
        indexes = [
            models.Index(fields=['client', 'broker_account'], name='idx_portfolio_client_ba'),
            models.Index(fields=['broker_account', 'name'], name='idx_portfolio_ba_name'),
            # If you frequently fetch by client alone, you can keep this:
            # models.Index(fields=['client'], name='idx_portfolio_client'),
        ]

        # unique_together = [("client", "broker_account", "name")]
        # indexes = [
        #     models.Index(fields=["client", "name"]),
        #     models.Index(fields=["client"]),
        # ]

    def __str__(self):
        return f"{self.client}:{self.name}"


class Position(TimeUUIDModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="positions")
    portfolio = models.ForeignKey(Portfolio, on_delete=models.CASCADE, related_name="positions")
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, related_name="positions")
    instrument = models.ForeignKey(Instrument, on_delete=models.PROTECT, related_name="positions")
    ibkr_con = models.ForeignKey(IbkrContract, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="positions")

    qty = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))
    avg_cost = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))
    market_price = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))
    market_value = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))
    asof_ts = models.DateTimeField()  # snapshot time

    class Meta:
        indexes = [
            models.Index(fields=["client", "broker_account", "asof_ts"]),
            models.Index(fields=["client", "portfolio", "instrument"]),
            models.Index(fields=["client", "asof_ts"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=['broker_account', 'instrument', 'asof_ts'],
                name='uniq_position_ba_instr_asof'
            ),
        ]
        get_latest_by = "asof_ts"
        ordering = ["-asof_ts"]


class Order(TimeUUIDModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="orders")
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, related_name="orders")
    ibkr_con = models.ForeignKey(IbkrContract, on_delete=models.SET_NULL, null=True, blank=True, related_name="orders")

    ibkr_order_id = models.BigIntegerField()  # not globally unique across accounts, hence composite uniqueness below
    parent_ibkr_order_id = models.BigIntegerField(null=True, blank=True)

    side = models.CharField(max_length=4)  # BUY/SELL
    order_type = models.CharField(max_length=8)  # LMT/MKT/etc.
    limit_price = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)
    aux_price = models.DecimalField(max_digits=20, decimal_places=6, null=True, blank=True)  # e.g., stop
    tif = models.CharField(max_length=8, blank=True, default="")  # DAY/GTC
    status = models.CharField(max_length=32, default="Unknown")
    raw = JSONField(default=dict, blank=True)

    created_ts = models.DateTimeField()
    updated_ts = models.DateTimeField()

    class Meta:
        unique_together = [("broker_account", "ibkr_order_id")]
        indexes = [
            models.Index(fields=["client", "broker_account"]),
            models.Index(fields=["client", "created_ts"]),
        ]

    def __str__(self):
        return f"{self.broker_account.account_code} #{self.ibkr_order_id} {self.side} {self.ibkr_con or ''} [{self.status}]"


class Execution(TimeUUIDModel):
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="executions")
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="executions")
    ibkr_exec_id = models.CharField(max_length=64, unique=True)

    fill_ts = models.DateTimeField()
    qty = models.DecimalField(max_digits=20, decimal_places=6)
    price = models.DecimalField(max_digits=20, decimal_places=6)
    fee = models.DecimalField(max_digits=20, decimal_places=6, default=Decimal("0"))
    venue = models.CharField(max_length=64, blank=True, default="")
    raw = JSONField(default=dict, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["client", "fill_ts"]),
        ]

    def __str__(self):
        return f"Exec {self.ibkr_exec_id} {self.qty}@{self.price}"


class OptionEvent(TimeUUIDModel):
    class EventType(models.TextChoices):
        ASSIGNMENT = "assignment", "Assignment"
        EXERCISE = "exercise", "Exercise"
        EXPIRATION = "expiration", "Expiration"

    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="option_events")
    broker_account = models.ForeignKey(BrokerAccount, on_delete=models.CASCADE, related_name="option_events")
    ibkr_con = models.ForeignKey(IbkrContract, on_delete=models.SET_NULL, null=True, blank=True,
                                 related_name="option_events")

    event_type = models.CharField(max_length=16, choices=EventType.choices)
    event_ts = models.DateTimeField()
    qty = models.DecimalField(max_digits=20, decimal_places=6)
    notes = models.TextField(blank=True, default="")

    class Meta:
        indexes = [
            models.Index(fields=["client", "event_ts"]),
            models.Index(fields=["client", "event_type"]),
        ]
