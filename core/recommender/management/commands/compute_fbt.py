"""
Management command: compute_fbt
--------------------------------
Computes 'Frequently Bought Together' relationships from purchase history
and writes them to the FrequentlyBoughtTogether table.

Usage:
    python manage.py compute_fbt
    python manage.py compute_fbt --watch   # loop every 10 minutes
"""
import time
from django.core.management.base import BaseCommand
from recommender.services import compute_fbt_scores


class Command(BaseCommand):
    help = "Compute Frequently Bought Together scores from purchase interactions"

    def add_arguments(self, parser):
        parser.add_argument(
            "--watch",
            action="store_true",
            help="Keep running and recompute every 10 minutes",
        )

    def handle(self, *args, **options):
        while True:
            self.stdout.write("[FBT] Computing co-purchase scores …")
            updated = compute_fbt_scores()
            self.stdout.write(
                self.style.SUCCESS(f"[FBT] Done — {updated} relationships upserted.")
            )
            if not options["watch"]:
                break
            self.stdout.write("[FBT] Sleeping 10 minutes …")
            time.sleep(600)
