from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional, Tuple

from django.core.exceptions import ImproperlyConfigured

from strategies.models import StrategyDefinition, StrategyVersion, StrategyInstance
from trading.strategies.config_schemas import DEFAULT_STRATEGY_SCHEMAS


@dataclass
class RegisteredStrategy:
    """
    Lightweight description of a loaded strategy implementation.
    """
    definition: StrategyDefinition
    version: StrategyVersion
    callable: Any  # usually a class implementing the strategy
    schema: Dict[str, Any]


def _load_object_from_code_ref(code_ref: str) -> Any:
    """
    Load a Python object from a "module.path:object_name" style reference.

    Examples:
      "trading.strategies.wheel:WheelStrategy"
    """
    if not code_ref:
        raise ImproperlyConfigured("StrategyVersion.code_ref is empty")

    if ":" not in code_ref:
        raise ImproperlyConfigured(
            f"Invalid code_ref '{code_ref}'. Expected format 'module.path:object_name'."
        )

    module_path, obj_name = code_ref.split(":", 1)
    try:
        module = importlib.import_module(module_path)
    except ImportError as exc:
        raise ImproperlyConfigured(
            f"Cannot import module '{module_path}' for strategy '{code_ref}': {exc}"
        ) from exc

    try:
        obj = getattr(module, obj_name)
    except AttributeError as exc:
        raise ImproperlyConfigured(
            f"Object '{obj_name}' not found in module '{module_path}' "
            f"for strategy '{code_ref}'."
        ) from exc

    return obj


def _get_effective_schema(version: StrategyVersion) -> Dict[str, Any]:
    """
    Return the JSON schema to use for this StrategyVersion.

    Priority:
      1) version.schema if non-empty
      2) DEFAULT_STRATEGY_SCHEMAS["<slug>:<version>"] if present
      3) empty dict (no validation)
    """
    if version.schema:
        return version.schema

    key = f"{version.strategy_def.slug}:{version.version}"
    return DEFAULT_STRATEGY_SCHEMAS.get(key, {})


def get_registered_strategy(version: StrategyVersion) -> RegisteredStrategy:
    """
    Load and wrap a StrategyVersion into a RegisteredStrategy.
    """
    impl = _load_object_from_code_ref(version.code_ref)
    schema = _get_effective_schema(version)

    return RegisteredStrategy(
        definition=version.strategy_def,
        version=version,
        callable=impl,
        schema=schema,
    )


def list_registered_strategies() -> List[RegisteredStrategy]:
    """
    Convenience function: load all StrategyVersions that have a non-empty code_ref.
    """
    registered: List[RegisteredStrategy] = []
    qs = StrategyVersion.objects.select_related("strategy_def").all()

    for version in qs:
        if not version.code_ref:
            continue
        try:
            registered.append(get_registered_strategy(version))
        except ImproperlyConfigured:
            # We intentionally swallow misconfigured versions here; the management
            # command can surface them explicitly if needed.
            continue

    return registered


def validate_config_against_schema(config: Dict[str, Any], schema: Dict[str, Any]) -> List[str]:
    """
    Very small JSON-schema-like validator.

    Supports:
      - type: "object"
      - properties: {name: {type: ...}}
      - required: [names]
      - additionalProperties: bool

    Returns: list of human-readable error messages. Empty list == valid.
    """
    errors: List[str] = []

    if not schema:
        return errors  # no schema -> nothing to validate

    if schema.get("type") == "object":
        if not isinstance(config, dict):
            errors.append(f"Expected object, got {type(config).__name__}")
            return errors

        props = schema.get("properties", {})
        required = schema.get("required", [])

        # Required fields present?
        for field in required:
            if field not in config:
                errors.append(f"Missing required field '{field}'")

        # Type checks for known properties
        for name, value in config.items():
            if name not in props:
                if schema.get("additionalProperties", True) is False:
                    errors.append(f"Unexpected field '{name}'")
                continue

            expected_type = props[name].get("type")
            if expected_type:
                if expected_type == "string" and not isinstance(value, str):
                    errors.append(f"Field '{name}' expected string, got {type(value).__name__}")
                elif expected_type == "boolean" and not isinstance(value, bool):
                    errors.append(f"Field '{name}' expected boolean, got {type(value).__name__}")
                elif expected_type == "number" and not isinstance(value, (int, float)):
                    errors.append(f"Field '{name}' expected number, got {type(value).__name__}")
                elif expected_type == "integer" and not isinstance(value, int):
                    errors.append(f"Field '{name}' expected integer, got {type(value).__name__}")
                elif expected_type == "array" and not isinstance(value, list):
                    errors.append(f"Field '{name}' expected array, got {type(value).__name__}")

    return errors
