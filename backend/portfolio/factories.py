import factory
from decimal import Decimal
from django.utils import timezone
from factory.django import DjangoModelFactory

from accounts.factories import ClientFactory, BrokerAccountFactory
from portfolio.models import (
    Instrument,
    IbkrContract,
    Portfolio,
    Position,
    Order,
    Execution,
    OptionEvent,
)


class InstrumentFactory(DjangoModelFactory):
    class Meta:
        model = Instrument

    symbol = factory.Sequence(lambda n: f"TICK{n}")
    name = factory.LazyAttribute(lambda obj: f"{obj.symbol} Corp")
    exchange = "SMART"
    asset_type = Instrument.AssetType.EQUITY
    currency = "USD"
    is_active = True


class IbkrContractFactory(DjangoModelFactory):
    class Meta:
        model = IbkrContract

    con_id = factory.Sequence(lambda n: 1000000 + n)
    instrument = factory.SubFactory(InstrumentFactory)
    sec_type = "STK"
    exchange = "SMART"
    currency = "USD"
    local_symbol = factory.LazyAttribute(lambda obj: obj.instrument.symbol)
    last_trade_date_or_contract_month = ""
    strike = None
    right = ""
    multiplier = None
    metadata = {}


class PortfolioFactory(DjangoModelFactory):
    class Meta:
        model = Portfolio

    client = factory.SubFactory(ClientFactory)
    name = factory.Sequence(lambda n: f"Portfolio {n}")
    base_currency = "USD"
    broker_account = factory.SubFactory(BrokerAccountFactory)
    metadata = {}


class PositionFactory(DjangoModelFactory):
    class Meta:
        model = Position

    client = factory.SubFactory(ClientFactory)
    portfolio = factory.SubFactory(PortfolioFactory)
    broker_account = factory.LazyAttribute(lambda obj: obj.portfolio.broker_account)
    instrument = factory.SubFactory(InstrumentFactory)
    ibkr_con = factory.SubFactory(IbkrContractFactory)

    qty = Decimal("100")
    avg_cost = Decimal("100.00")
    market_price = Decimal("105.00")
    market_value = Decimal("10500.00")
    asof_ts = factory.LazyFunction(timezone.now)


class OrderFactory(DjangoModelFactory):
    class Meta:
        model = Order

    client = factory.SubFactory(ClientFactory)
    broker_account = factory.SubFactory(BrokerAccountFactory)
    ibkr_con = factory.SubFactory(IbkrContractFactory)

    ibkr_order_id = factory.Sequence(lambda n: 5000 + n)
    parent_ibkr_order_id = None

    side = "BUY"          # or "SELL"
    order_type = "LMT"    # LMT / MKT / etc.
    limit_price = Decimal("1.23")
    aux_price = None
    tif = "DAY"
    status = "Submitted"
    raw = {}

    created_ts = factory.LazyFunction(timezone.now)
    updated_ts = factory.LazyFunction(timezone.now)


class ExecutionFactory(DjangoModelFactory):
    class Meta:
        model = Execution

    client = factory.SubFactory(ClientFactory)
    order = factory.SubFactory(OrderFactory)
    ibkr_exec_id = factory.Sequence(lambda n: f"EX{n:06d}")

    fill_ts = factory.LazyFunction(timezone.now)
    qty = Decimal("1")
    price = Decimal("1.23")
    fee = Decimal("0.50")
    venue = "SMART"
    raw = {}


class OptionEventFactory(DjangoModelFactory):
    class Meta:
        model = OptionEvent

    client = factory.SubFactory(ClientFactory)
    broker_account = factory.SubFactory(BrokerAccountFactory)
    ibkr_con = factory.SubFactory(IbkrContractFactory)

    event_type = OptionEvent.EventType.ASSIGNMENT
    event_ts = factory.LazyFunction(timezone.now)
    qty = Decimal("100")
    notes = ""
