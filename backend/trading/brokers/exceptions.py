# trading/brokers/exceptions.py

class BrokerError(Exception):
    """
    Base exception for all broker-related errors.
    """
    pass


class UnsupportedBrokerError(BrokerError):
    """
    Raised when a BrokerAccount.kind or configuration
    cannot be mapped to a concrete BrokerAPI implementation.
    """
    pass


class BrokerConfigError(BrokerError):
    """
    Raised when broker configuration (env vars, settings, account_code, etc.)
    is missing or invalid.
    """
    pass


class BrokerConnectionError(BrokerError):
    """
    Raised when the connector cannot establish or maintain a connection
    to the underlying broker API.
    """
    pass
