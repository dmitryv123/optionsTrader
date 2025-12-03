from __future__ import annotations

from typing import Dict, TypedDict, Literal, Optional, Any


# ---- Python typing for configs ------------------------------------------------
# These are *examples* for v1 strategies. We can extend later as we implement
# more strategy classes.


class BaseStrategyConfig(TypedDict, total=False):
    """Common optional fields shared by most strategies."""
    enabled: bool
    capital_fraction: float  # 0.0–1.0 fraction of portfolio allocated
    notes: str


class WheelConfig(BaseStrategyConfig, total=False):
    """
    v1 Wheel strategy config.

    slug: "wheel"
    version: "v1"
    """
    underlying_universe: list[str]  # ticker symbols, e.g. ["AAPL", "MSFT"]
    min_dte: int
    max_dte: int
    target_delta: float
    max_positions: int
    min_premium_annualized_ror: float
    allow_assigned: bool


class ThetaFarmConfig(BaseStrategyConfig, total=False):
    """
    v1 Theta farming / short premium config.

    slug: "theta_farm"
    version: "v1"
    """
    underlying_universe: list[str]
    min_dte: int
    max_dte: int
    max_short_vega: float
    max_short_gamma: float
    max_margin_utilization: float
    max_positions: int


class SteadyCollarConfig(BaseStrategyConfig, total=False):
    """
    v1 Steady collar config.

    slug: "steady_collar"
    version: "v1"
    """
    underlying_universe: list[str]
    target_delta: float
    put_dte: int
    call_dte: int
    rebalance_days: int
    max_underlying_weight: float


# ---- JSON Schemas -------------------------------------------------------------
# These are deliberately simple JSON Schemas (no advanced constructs) so we can
# validate them without external dependencies.


WheelConfigSchema: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "enabled": {"type": "boolean"},
        "capital_fraction": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "notes": {"type": "string"},
        "underlying_universe": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "min_dte": {"type": "integer", "minimum": 1},
        "max_dte": {"type": "integer", "minimum": 1},
        "target_delta": {"type": "number"},
        "max_positions": {"type": "integer", "minimum": 1},
        "min_premium_annualized_ror": {"type": "number"},
        "allow_assigned": {"type": "boolean"},
    },
    "required": ["underlying_universe", "min_dte", "max_dte", "target_delta"],
    "additionalProperties": False,
}

ThetaFarmConfigSchema: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "enabled": {"type": "boolean"},
        "capital_fraction": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "notes": {"type": "string"},
        "underlying_universe": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "min_dte": {"type": "integer", "minimum": 1},
        "max_dte": {"type": "integer", "minimum": 1},
        "max_short_vega": {"type": "number"},
        "max_short_gamma": {"type": "number"},
        "max_margin_utilization": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "max_positions": {"type": "integer", "minimum": 1},
    },
    "required": ["underlying_universe", "min_dte", "max_dte"],
    "additionalProperties": False,
}

SteadyCollarConfigSchema: Dict[str, Any] = {
    "type": "object",
    "properties": {
        "enabled": {"type": "boolean"},
        "capital_fraction": {"type": "number", "minimum": 0.0, "maximum": 1.0},
        "notes": {"type": "string"},
        "underlying_universe": {
            "type": "array",
            "items": {"type": "string"},
            "minItems": 1,
        },
        "target_delta": {"type": "number"},
        "put_dte": {"type": "integer", "minimum": 1},
        "call_dte": {"type": "integer", "minimum": 1},
        "rebalance_days": {"type": "integer", "minimum": 1},
        "max_underlying_weight": {"type": "number", "minimum": 0.0, "maximum": 1.0},
    },
    "required": ["underlying_universe", "target_delta", "put_dte", "call_dte"],
    "additionalProperties": False,
}


# Keyed by "<slug>:<version>" so we can use it as a fallback when seeding
# StrategyVersion.schema or when a DB row has an empty schema.
DEFAULT_STRATEGY_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "wheel:v1": WheelConfigSchema,
    "theta_farm:v1": ThetaFarmConfigSchema,
    "steady_collar:v1": SteadyCollarConfigSchema,
}
