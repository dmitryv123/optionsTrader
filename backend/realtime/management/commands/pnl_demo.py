from django.core.management.base import BaseCommand
import random
import time
from realtime.publishers import publish_pnl


class Command(BaseCommand):
    help = "Emit demo PnL ticks every second"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting PnL demo stream (Ctrl+C to stop)"))
        while True:
            publish_pnl(random.uniform(-500, 500))
            time.sleep(1)
