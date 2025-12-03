from __future__ import annotations

from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from strategies.models import StrategyInstance
from trading.strategies.executor import run_strategy_instance


class Command(BaseCommand):
    help = (
        "Run a single StrategyInstance via the strategy executor, "
        "print PlannedActions, and optionally persist Recommendations."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--instance-id",
            type=str,
            help="UUID of the StrategyInstance to run.",
        )
        parser.add_argument(
            "--instance-name",
            type=str,
            help="Name of the StrategyInstance (must be unique per client).",
        )
        parser.add_argument(
            "--client-id",
            type=str,
            help="Client UUID (required if using --instance-name).",
        )
        parser.add_argument(
            "--asof-ts",
            type=str,
            default=None,
            help="Optional ISO timestamp for context (default: now).",
        )
        parser.add_argument(
            "--persist",
            # action="bool",
            nargs="?",
            const=True,
            default=False,
            help="If set, persist actions as Recommendation rows.",
        )

    def handle(self, *args, **options):
        instance = self._resolve_instance(options)
        if instance is None:
            raise CommandError(
                "You must specify either --instance-id or (--instance-name and --client-id).")

        asof_ts_str = options.get("asof_ts")
        if asof_ts_str:
            try:
                # Let Django parse; if naïve, executor will make it aware.
                asof_ts = timezone.datetime.fromisoformat(asof_ts_str)
            except Exception as exc:
                raise CommandError(f"Invalid --asof-ts value: {exc}")
        else:
            asof_ts = None

        persist = options.get("persist")

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"Running StrategyInstance {instance.id} "
                f"({instance.client}:{instance.name})"
            )
        )

        actions = run_strategy_instance(
            instance=instance,
            asof_ts=asof_ts,
            persist_recommendations=persist,
        )

        if not actions:
            self.stdout.write("No PlannedActions returned.")
            return

        self.stdout.write(f"{len(actions)} PlannedAction(s) returned:\n")
        for idx, act in enumerate(actions, start=1):
            self.stdout.write(f"{idx}. action={act.action!r}")
            self.stdout.write(f"   underlier={getattr(act.underlier, 'symbol', None)!r}")
            self.stdout.write(f"   confidence={str(act.confidence)}")
            self.stdout.write(f"   rationale={act.rationale!r}")
            self.stdout.write(f"   params={act.params!r}")
            self.stdout.write("")

        if persist:
            self.stdout.write(self.style.SUCCESS("Recommendations persisted."))

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    def _resolve_instance(self, options) -> Optional[StrategyInstance]:
        print ('options:',options)
        instance_id = options.get("instance-id")  # For some reason it did not work , need to ask AI later

        print('instance-id',instance_id)
        instance_id = 'a41b42e1-af23-4fb1-8f6e-ddfa2a8437ec'
        instance_name = options.get("instance-name")
        client_id = options.get("client-id")

        if instance_id:
            try:
                return StrategyInstance.objects.get(id=instance_id)
            except StrategyInstance.DoesNotExist:
                raise CommandError(f"StrategyInstance with id={instance_id!r} not found.")

        if instance_name and client_id:
            try:
                return StrategyInstance.objects.get(
                    client_id=client_id,
                    name=instance_name,
                )
            except StrategyInstance.DoesNotExist:
                raise CommandError(
                    f"StrategyInstance with name={instance_name!r} and client_id={client_id!r} not found."
                )

        return None
