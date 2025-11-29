# trading/brokers/registry.py

from __future__ import annotations
from typing import TYPE_CHECKING

from accounts.models import BrokerAccount
from .base import BrokerAPI
from .exceptions import UnsupportedBrokerError

if TYPE_CHECKING:
    # Avoid circular import issues at runtime; only used for type-checkers
    from .ibkr.client import IBKRClient  # pragma: no cover


def get_broker_client(broker_account: BrokerAccount) -> BrokerAPI:
    """
    Given a BrokerAccount ORM instance, return a concrete BrokerAPI client.

    For now, this router only supports IBKR-backed accounts (LIVE and PAPER).
    SIM accounts and other kinds will be wired later.

    This function is the main entry point for ingestion and higher-level
    logic; nothing outside this module should instantiate IBKRClient directly.
    """
    from .ibkr.client import IBKRClient  # local import to avoid circulars

    kind = broker_account.kind

    # Map LIVE and PAPER_LINKED to IBKRClient
    if kind in (BrokerAccount.Kind.LIVE, BrokerAccount.Kind.PAPER_LINKED):
        return IBKRClient.from_broker_account(broker_account)

    # SIM / other brokers not implemented yet
    raise UnsupportedBrokerError(
        f"Unsupported broker kind for account {broker_account.account_code!r}: {kind}"
    )
