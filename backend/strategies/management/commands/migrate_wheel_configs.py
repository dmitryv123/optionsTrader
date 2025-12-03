from __future__ import annotations

from typing import Any, Dict

from django.core.management.base import BaseCommand

from strategies.models import StrategyInstance


class Command(BaseCommand):
    help = (
        "Migrate Wheel StrategyInstance.config from older key names "
        "(e.g. put_days_out, put_delta_target) to the newer schema "
        "(min_dte, target_delta). By default runs in DRY-RUN mode."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Persist changes to the database. Without this flag, runs as a dry-run.",
        )

        parser.add_argument(
            "--slug",
            type=str,
            default="wheel",
            help="StrategyDefinition.slug to migrate (default: wheel).",
        )

        parser.add_argument(
            "--ver1",
            type=str,
            default="v1",
            help="StrategyVersion.version to migrate (default: v1).",
        )

    def handle(self, *args, **options):
        apply_changes = options["apply"]
        slug = options["slug"]
        version = options["ver1"]

        qs = StrategyInstance.objects.select_related("strategy_version", "strategy_version__strategy_def").filter(
            strategy_version__strategy_def__slug=slug,
            strategy_version__version=version,
        )

        if not qs.exists():
            self.stdout.write(
                self.style.WARNING(
                    f"No StrategyInstance records found for slug={slug!r}, version={version!r}."
                )
            )
            return

        mode_label = "APPLY" if apply_changes else "DRY-RUN"
        self.stdout.write(self.style.MIGRATE_HEADING(f"Wheel config migration ({mode_label})"))
        self.stdout.write(
            f"Scanning {qs.count()} StrategyInstance(s) for slug={slug!r}, version={version!r}..."
        )

        migrated_count = 0
        unchanged_count = 0

        for inst in qs:
            original_config = inst.config or {}
            new_config, changed = self._migrate_single_config(original_config)

            if not changed:
                unchanged_count += 1
                continue

            migrated_count += 1

            self.stdout.write(
                self.style.MIGRATE_LABEL(
                    f"- {inst.client}:{inst.name} ({slug}@{version})"
                )
            )
            self.stdout.write("  Original config:")
            self._print_dict(original_config, indent="    ")
            self.stdout.write("  Migrated config:")
            self._print_dict(new_config, indent="    ")

            if apply_changes:
                inst.config = new_config
                inst.save(update_fields=["config"])

        self.stdout.write("")
        self.stdout.write(
            f"Migration complete. Migrated={migrated_count}, unchanged={unchanged_count}, "
            f"total={migrated_count + unchanged_count}."
        )

        if not apply_changes and migrated_count > 0:
            self.stdout.write(
                self.style.WARNING(
                    "No changes were written (dry-run). "
                    "Re-run with --apply to persist migration."
                )
            )

    def _migrate_single_config(self, config: Dict[str, Any]) -> (Dict[str, Any], bool):
        """
        Take a single config dict and add new keys where we can safely infer
        them from old keys. We NEVER delete anything here, only add/duplicate.

        Old keys we know about from your legacy schema:
          - put_days_out        -> new 'min_dte' (and optionally 'max_dte' if missing)
          - put_delta_target    -> new 'target_delta'

        Returns (new_config, changed_flag).
        """
        if not isinstance(config, dict):
            # If it's not even a dict, we won't try to touch it.
            return config, False

        new_config = dict(config)  # shallow copy
        changed = False

        # 1) put_days_out -> min_dte / max_dte
        if "put_days_out" in config:
            if "min_dte" not in new_config:
                new_config["min_dte"] = config["put_days_out"]
                changed = True
            if "max_dte" not in new_config:
                # Reasonable assumption: if old config had only one "days-out"
                # parameter, we treat it as both min and max for now.
                new_config["max_dte"] = config["put_days_out"]
                changed = True

        # 2) put_delta_target -> target_delta
        if "put_delta_target" in config and "target_delta" not in new_config:
            new_config["target_delta"] = config["put_delta_target"]
            changed = True

        return new_config, changed

    def _print_dict(self, data: Dict[str, Any], indent: str = ""):
        if not data:
            self.stdout.write(f"{indent}{{}}")
            return
        for key, value in data.items():
            self.stdout.write(f"{indent}{key!r}: {value!r}")
