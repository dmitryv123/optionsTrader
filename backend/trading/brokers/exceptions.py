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

class BrokerDataMappingError(BrokerError):
    """
    Raised when a raw broker payload cannot be mapped into one of the
    normalized dataclasses (OrderData, ExecutionData, OptionEventData, etc.).

    This usually indicates a schema change, missing fields, or unexpected
    types that should be investigated and fixed in the mapper layer.
    """
    pass


class BrokerRateLimitError(BrokerError):
    """
    Raised when the broker API indicates rate limiting or throttling.

    Higher-level code can catch this error and apply backoff, retry, or
    scheduling adjustments to avoid hammering the broker endpoints.
    """
    pass
