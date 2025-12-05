
# ./manage.py inspect_runs --instance-id <UUID> --limit 5 --show-actions --show-signals  TODO DV!


from __future__ import annotations

from django.core.management.base import BaseCommand, CommandError

from strategies.models import StrategyInstance
from trading.strategies.inspection import (
    get_last_runs,
    get_last_recommendations,
    get_last_signals,
)


class Command(BaseCommand):
    help = "Inspect recent StrategyRuns and optionally show recommendations/signals."

    def add_arguments(self, parser):
        parser.add_argument("--instance-id", required=True)
        parser.add_argument("--limit", type=int, default=10)
        parser.add_argument("--show-actions", action="store_true")
        parser.add_argument("--show-signals", action="store_true")

    def handle(self, *args, **options):
        instance_id = options["instance_id"]
        limit = options["limit"]

        try:
            instance = StrategyInstance.objects.get(id=instance_id)
        except StrategyInstance.DoesNotExist:
            raise CommandError(f"StrategyInstance {instance_id!r} not found")

        self.stdout.write(f"Inspecting StrategyInstance {instance.id} ({instance.client}:{instance.name})\n")

        runs = get_last_runs(instance.id, limit)
        self.stdout.write(f"Last {len(runs)} runs:\n")

        for r in runs:
            self.stdout.write(
                f"- {r.run_ts} | status={r.status} | "
                f"duration={r.duration_ms}ms | "
                f"num_actions={r.stats.get('num_actions')}"
            )
            if r.error_trace:
                self.stdout.write("  ERROR TRACE:")
                self.stdout.write(r.error_trace)

        if options["show_actions"]:
            recs = get_last_recommendations(instance.id, limit)
            self.stdout.write(f"\nLast {len(recs)} recommendations:\n")
            for rec in recs:
                self.stdout.write(
                    f"- {rec.asof_ts} | action={rec.action} | "
                    f"conf={rec.confidence} | underlier={getattr(rec.underlier, 'symbol', None)}"
                )

        if options["show_signals"]:
            sigs = get_last_signals(instance.id, limit)
            self.stdout.write(f"\nLast {len(sigs)} signals:\n")
            for sig in sigs:
                self.stdout.write(
                    f"- {sig.asof_ts} | type={sig.type} | payload={sig.payload}"
                )
