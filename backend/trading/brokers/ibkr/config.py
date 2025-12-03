# trading/brokers/ibkr/config.py

from __future__ import annotations
from dataclasses import dataclass
import os
from typing import Optional

try:
    from django.conf import settings
except Exception:  # pragma: no cover - allows use without Django context
    settings = None


@dataclass
class IBKRConnectionConfig:
    """
    Connection configuration for IBKR (Gateway or TWS).

    This config is deliberately simple and broker-neutral enough that it can
    be instantiated from environment variables, Django settings, or any other
    configuration layer.
    """
    host: str
    port: int
    client_id: int
    use_gateway: bool = True

    def __repr__(self) -> str:
        # Avoid accidentally logging secrets (none here anyway, but keep it clean)
        return (
            f"IBKRConnectionConfig(host={self.host!r}, port={self.port}, "
            f"client_id={self.client_id}, use_gateway={self.use_gateway})"
        )


def _get_setting(name: str, default: Optional[str] = None) -> Optional[str]:
    """
    Helper that checks Django settings first (if available), then environment.
    """
    # 1) Django settings if available
    if settings is not None and hasattr(settings, name):
        value = getattr(settings, name)
        # Normalize to string for downstream conversion (port, client_id, bool)
        return str(value)

    # 2) Environment variable
    return os.getenv(name, default)


def get_ibkr_connection_config(prefix: str = "IBKR_") -> IBKRConnectionConfig:
    """
    Build an IBKRConnectionConfig from Django settings and/or environment variables.

    Resolution order for each parameter:
      1) Django settings.<PREFIX>HOST / PORT / CLIENT_ID / USE_GATEWAY
      2) Environment variables IBKR_HOST / IBKR_PORT / IBKR_CLIENT_ID / IBKR_USE_GATEWAY
      3) Hard-coded defaults if neither is set

    Expected settings / env vars:
      - IBKR_HOST         (default: "127.0.0.1")
      - IBKR_PORT         (default: "4001"  -> typical Gateway live port)
      - IBKR_CLIENT_ID    (default: "1")
      - IBKR_USE_GATEWAY  (default: "true")

    Example (Django settings.py):
        IBKR_HOST = "127.0.0.1"
        IBKR_PORT = 4002
        IBKR_CLIENT_ID = 7
        IBKR_USE_GATEWAY = False

    Example (environment):
        export IBKR_HOST=127.0.0.1
        export IBKR_PORT=4001
        export IBKR_CLIENT_ID=1
        export IBKR_USE_GATEWAY=true
    """
    host = _get_setting(f"{prefix}HOST", "127.0.0.1")
    port_str = _get_setting(f"{prefix}PORT", "4001")
    client_id_str = _get_setting(f"{prefix}CLIENT_ID", "1")
    use_gateway_str = _get_setting(f"{prefix}USE_GATEWAY", "true")

    port = int(port_str) if port_str is not None else 4001
    client_id = int(client_id_str) if client_id_str is not None else 1
    use_gateway = str(use_gateway_str).lower() in ("1", "true", "yes", "y", "on")

    return IBKRConnectionConfig(
        host=host,
        port=port,
        client_id=client_id,
        use_gateway=use_gateway,
    )
