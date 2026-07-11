import time

from django.core.management.base import BaseCommand

from receipts.worker import process_next_ocr_job


class Command(BaseCommand):
    help = "Process pending PaddleOCR jobs from the database queue."

    def add_arguments(self, parser):
        parser.add_argument("--once", action="store_true", help="Process at most one queued job and exit.")
        parser.add_argument("--poll-seconds", type=float, default=2.0)

    def handle(self, *args, **options):
        while True:
            processed = process_next_ocr_job()
            if options["once"]:
                return
            if not processed:
                time.sleep(options["poll_seconds"])
