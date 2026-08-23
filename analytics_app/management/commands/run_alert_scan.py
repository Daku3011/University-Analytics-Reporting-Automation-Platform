"""Run the alert scan (#6) on demand: python manage.py run_alert_scan"""
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = 'Run the automated alert scan (missing data / stale status / big changes).'

    def add_arguments(self, parser):
        parser.add_argument(
            '--with-digest', action='store_true',
            help='Also send the alert email digest after scanning.')

    def handle(self, *args, **options):
        from analytics_app.services.alert_engine import run_alert_scan

        summary = run_alert_scan()
        self.stdout.write(
            f"Scan {summary['year']}: {summary['created']} created, "
            f"{summary['updated']} refreshed, {summary['resolved']} auto-resolved, "
            f"{summary['open_total']} open.")
        if options['with_digest']:
            from analytics_app.services.alert_digest import send_alert_digest
            sent = send_alert_digest()
            self.stdout.write(self.style.SUCCESS(f'Digest emails sent: {sent}'))
