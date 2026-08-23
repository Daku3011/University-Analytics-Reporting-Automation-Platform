"""Celery tasks for analytics_app."""
from celery import shared_task


@shared_task
def run_daily_alert_scan():
    """Nightly beat job (#6): detect alerts, then email the digest."""
    from analytics_app.services.alert_digest import send_alert_digest
    from analytics_app.services.alert_engine import run_alert_scan

    summary = run_alert_scan()
    emails_sent = send_alert_digest()
    return {'scan': summary, 'digest_emails_sent': emails_sent}
