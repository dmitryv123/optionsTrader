import factory
from django.conf import settings
from django.utils import timezone
from factory.django import DjangoModelFactory

from .models import Client, ClientMembership, BrokerAccount, AccountSnapshot


class ClientFactory(DjangoModelFactory):
    class Meta:
        model = Client

    name = factory.Sequence(lambda n: f"Client {n}")
    is_active = True
    settings = {}  # can override per test


class BrokerAccountFactory(DjangoModelFactory):
    class Meta:
        model = BrokerAccount

    client = factory.SubFactory(ClientFactory)
    kind = BrokerAccount.Kind.LIVE
    account_code = factory.Sequence(lambda n: f"U{1000+n}")
    base_currency = "USD"
    nickname = factory.LazyAttribute(lambda obj: f"{obj.client.name} - {obj.account_code}")
    metadata = {}


class UserFactory(DjangoModelFactory):
    """
    Basic user factory. Adjust fields to match your AUTH_USER_MODEL.
    If you're using Django's default User model, this is fine.
    If you have a custom user model, tweak the fields accordingly.
    """
    class Meta:
        model = settings.AUTH_USER_MODEL

    username = factory.Sequence(lambda n: f"user{n}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@example.com")
    is_active = True


class ClientMembershipFactory(DjangoModelFactory):
    class Meta:
        model = ClientMembership

    client = factory.SubFactory(ClientFactory)
    user = factory.SubFactory(UserFactory)
    role = ClientMembership.Role.VIEWER


class AccountSnapshotFactory(DjangoModelFactory):
    class Meta:
        model = AccountSnapshot

    client = factory.SubFactory(ClientFactory)
    broker_account = factory.SubFactory(BrokerAccountFactory)
    asof_ts = factory.LazyFunction(timezone.now)
    currency = "USD"

    cash = "100000.00"
    buying_power = "200000.000000"
    maintenance_margin = "50000.000000"
    used_margin = "40000.000000"
    extras = {}
