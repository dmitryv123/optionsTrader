import uuid
from decimal import Decimal
from django.utils import timezone
from factory import Sequence, LazyFunction, LazyAttribute, SubFactory
from factory.django import DjangoModelFactory

from accounts.factories import ClientFactory, BrokerAccountFactory
from portfolio.factories import PortfolioFactory, InstrumentFactory, IbkrContractFactory
from strategies.models import (
    StrategyDefinition,
    StrategyVersion,
    StrategyInstance,
    StrategyRun,
    Signal,
    Opportunity,
    Recommendation,
)


class StrategyDefinitionFactory(DjangoModelFactory):
    class Meta:
        model = StrategyDefinition

    name = Sequence(lambda n: f"Strategy {n}")
    slug = Sequence(lambda n: f"strategy-{n}")
    description = ""


class StrategyVersionFactory(DjangoModelFactory):
    class Meta:
        model = StrategyVersion

    strategy_def = SubFactory(StrategyDefinitionFactory)
    version = "v1"
    schema = {}
    code_ref = ""


class StrategyInstanceFactory(DjangoModelFactory):
    class Meta:
        model = StrategyInstance

    client = SubFactory(ClientFactory)
    name = Sequence(lambda n: f"Instance {n}")
    strategy_version = SubFactory(StrategyVersionFactory)
    portfolio = SubFactory(PortfolioFactory)
    enabled = True
    tags = ""
    config = {}


class StrategyRunFactory(DjangoModelFactory):
    class Meta:
        model = StrategyRun

    strategy_instance = SubFactory(StrategyInstanceFactory)
    run_ts = LazyFunction(timezone.now)
    mode = StrategyRun.Mode.DAILY
    status = "ok"
    stats = {}
    errors = {}


class SignalFactory(DjangoModelFactory):
    class Meta:
        model = Signal

    client = SubFactory(ClientFactory)
    strategy_instance = SubFactory(StrategyInstanceFactory)
    asof_ts = LazyFunction(timezone.now)
    portfolio = SubFactory(PortfolioFactory)
    underlier = SubFactory(InstrumentFactory)
    ibkr_con = SubFactory(IbkrContractFactory)

    type = "generic_signal"
    payload = {}


class OpportunityFactory(DjangoModelFactory):
    class Meta:
        model = Opportunity

    client = SubFactory(ClientFactory)
    asof_ts = LazyFunction(timezone.now)
    underlier = SubFactory(InstrumentFactory)
    ibkr_con = SubFactory(IbkrContractFactory)

    metrics = {"ror_pct": 1.23, "delta": -0.25}
    required_margin = Decimal("1000.00")
    notes = ""


class RecommendationFactory(DjangoModelFactory):
    class Meta:
        model = Recommendation

    client = SubFactory(ClientFactory)
    portfolio = SubFactory(PortfolioFactory)
    broker_account = SubFactory(BrokerAccountFactory)

    strategy_instance = SubFactory(StrategyInstanceFactory)
    strategy_version = LazyAttribute(lambda obj: obj.strategy_instance.strategy_version)

    asof_ts = LazyFunction(timezone.now)
    underlier = SubFactory(InstrumentFactory)
    ibkr_con = SubFactory(IbkrContractFactory)

    action = "sell_put"
    params = {"strike": 100, "expiry": "2025-12-19", "qty": 1, "limit_price": 2.5}

    confidence = Decimal("75.00")
    rationale = "Test recommendation"
    plan_id = LazyFunction(uuid.uuid4)

    opportunity = SubFactory(OpportunityFactory)
