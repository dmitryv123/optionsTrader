from __future__ import annotations

from typing import Any, Dict, List

from django.core.management.base import BaseCommand, CommandError

from strategies.models import StrategyDefinition, StrategyVersion, StrategyInstance
from trading.strategies.registry import (
    get_registered_strategy,
    list_registered_strategies,
    validate_config_against_schema,
)


class Command(BaseCommand):
    help = "List registered strategies, versions, and optionally validate instance configs."

    def add_arguments(self, parser):
        parser.add_argument(
            "--validate-configs",
            action="store_true",
            help="Validate StrategyInstance.config against StrategyVersion.schema.",
        )

    def handle(self, *args, **options):
        validate_configs: bool = options["validate_configs"]

        self.stdout.write(self.style.MIGRATE_HEADING("Strategy Definitions & Versions"))

        versions = StrategyVersion.objects.select_related("strategy_def").order_by(
            "strategy_def__name", "version"
        )

        if not versions.exists():
            self.stdout.write("No StrategyVersion records found.")
            return

        for ver in versions:
            self.stdout.write(
                f"- {ver.strategy_def.name} "
                f"(slug={ver.strategy_def.slug}, version={ver.version}, "
                f"code_ref={ver.code_ref or '-'}, schema_keys={list(ver.schema.keys()) if ver.schema else []})"
            )

        self.stdout.write("")  # newline

        # Try to load implementations
        self.stdout.write(self.style.MIGRATE_HEADING("Registered Implementations (code_ref-resolved)"))
        loaded = list_registered_strategies()
        if not loaded:
            self.stdout.write("No StrategyVersion with valid code_ref loaded.")
        else:
            for rs in loaded:
                self.stdout.write(
                    f"- {rs.definition.slug}@{rs.version.version}: {rs.callable} "
                    f"(schema: {bool(rs.schema)})"
                )

        if not validate_configs:
            return

        self.stdout.write("")
        self.stdout.write(self.style.MIGRATE_HEADING("Config Validation (StrategyInstance)"))

        instances = StrategyInstance.objects.select_related(
            "strategy_version",
            "strategy_version__strategy_def",
        ).all()

        if not instances.exists():
            self.stdout.write("No StrategyInstance records to validate.")
            return

        total = 0
        errors_total = 0

        for inst in instances:
            total += 1
            version = inst.strategy_version
            schema = version.schema or {}
            rs = None

            # Best-effort: try to resolve the registered strategy (not required for validation)
            try:
                rs = get_registered_strategy(version)
                schema = rs.schema
            except Exception:
                # If load fails, we still can validate config using only DB schema.
                pass

            config = inst.config or {}
            error_list = validate_config_against_schema(config, schema)
            if error_list:
                errors_total += 1
                self.stdout.write(
                    self.style.ERROR(
                        f"[INVALID] {inst.client}:{inst.name} "
                        f"({version.strategy_def.slug}@{version.version})"
                    )
                )
                for err in error_list:
                    self.stdout.write(f"  - {err}")
            else:
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[OK] {inst.client}:{inst.name} "
                        f"({version.strategy_def.slug}@{version.version})"
                    )
                )

        self.stdout.write("")
        self.stdout.write(
            f"Validated {total} StrategyInstance(s); "
            f"{errors_total} with errors, {total - errors_total} OK."
        )
