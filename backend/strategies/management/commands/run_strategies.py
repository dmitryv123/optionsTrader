from __future__ import annotations

from datetime import datetime
from typing import Optional

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from trading.strategies.orchestration import run_all_enabled_strategies
from strategies.models import StrategyInstance


class Command(BaseCommand):
    help = "Run one or more strategies via the Strategy Engine."

    def add_arguments(self, parser):
        # T0059.2 --strategy and --dry-run
        parser.add_argument(
            "--strategy",
            dest="strategy_slug",
            help="Optional strategy slug to filter (e.g. 'wheel')",
        )
        parser.add_argument(
            "--instance-id",
            dest="instance_id",
            help="Optional StrategyInstance id to run only one instance",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Do not persist recommendations; still evaluate strategies.",
        )
        parser.add_argument(
            "--asof",
            dest="asof",
            help="Optional as-of timestamp (ISO 8601, default=now)",
        )

    def handle(self, *args, **options):
        strategy_slug = options.get("strategy_slug")
        instance_id = options.get("instance_id")
        dry_run = bool(options.get("dry_run"))
        asof_str = options.get("asof")

        if instance_id and strategy_slug:
            raise CommandError("Use either --instance-id OR --strategy, not both.")

        asof_ts: Optional[datetime] = None
        if asof_str:
            try:
                asof_ts = datetime.fromisoformat(asof_str)
                if timezone.is_naive(asof_ts):
                    asof_ts = timezone.make_aware(asof_ts, timezone.get_current_timezone())
            except Exception:
                raise CommandError(f"Invalid --asof format, expected ISO 8601, got: {asof_str!r}")

        # If instance_id is provided, we just run that single instance
        if instance_id:
            try:
                instance = StrategyInstance.objects.get(id=instance_id, enabled=True)
            except StrategyInstance.DoesNotExist:
                raise CommandError(f"StrategyInstance {instance_id!r} not found or not enabled.")

            self.stdout.write(f"Running single StrategyInstance {instance.id} ({instance.client}:{instance.name})\n")

            summaries = run_all_enabled_strategies(
                asof_ts=asof_ts,
                strategy_slug=None,
                dry_run=dry_run,
            )
            # Filter to our instance
            summaries = [s for s in summaries if s["instance_id"] == str(instance.id)]
        else:
            self.stdout.write("Running all enabled strategies\n")
            if strategy_slug:
                self.stdout.write(f"  (filtered by strategy slug={strategy_slug})\n")

            summaries = run_all_enabled_strategies(
                asof_ts=asof_ts,
                strategy_slug=strategy_slug,
                dry_run=dry_run,
            )

        # T0059.3 — per-strategy and global stats
        total_actions = 0
        total_signals = 0
        total_opps = 0
        total_recs = 0

        self.stdout.write("\nPer-strategy results:\n")

        for s in summaries:
            self.stdout.write(
                f"- {s['client']}:{s['name']} "
                f"(strategy={s['strategy']}, instance_id={s['instance_id']})\n"
                f"    status={s['status']} dry_run={s['dry_run']} "
                f"actions={s['num_actions']} "
                f"signals={s['num_signals']} "
                f"opportunities={s['num_opportunities']} "
                f"recommendations={s['num_recommendations']}\n"
            )

            total_actions += s["num_actions"]
            total_signals += s["num_signals"]
            total_opps += s["num_opportunities"]
            total_recs += s["num_recommendations"]

        self.stdout.write("\nGlobal summary:\n")
        self.stdout.write(f"  strategies_run = {len(summaries)}\n")
        self.stdout.write(f"  total_actions  = {total_actions}\n")
        self.stdout.write(f"  total_signals  = {total_signals}\n")
        self.stdout.write(f"  total_opps     = {total_opps}\n")
        self.stdout.write(f"  total_recs     = {total_recs}\n")
