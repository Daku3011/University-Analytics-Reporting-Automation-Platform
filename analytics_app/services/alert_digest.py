"""Email digest for new unresolved alerts (#6).

Recipients are scoped by role: super admins receive every unresolved alert
that has not been emailed yet; college admins receive only their own
institute's. Every alert that goes out in any digest is stamped with
``notified_at`` so the next run only picks up genuinely new ones.
"""
import logging

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from django.utils import timezone

from analytics_app.models import Alert

logger = logging.getLogger(__name__)

CATEGORY_LABELS = dict(Alert._meta.get_field('category').choices)
LEVEL_LABELS = dict(Alert._meta.get_field('level').choices)


def _recipients():
    """(user, college-or-None) pairs for everyone who should get a digest."""
    pairs = []
    supers = (User.objects.filter(is_active=True)
              .filter(Q(profile__role='super_admin') | Q(is_superuser=True))
              .exclude(email='').distinct())
    for u in supers:
        pairs.append((u, None))
    admins = (User.objects.filter(
        is_active=True,
        profile__role='college_admin',
        profile__college__isnull=False,
    ).exclude(email='').distinct())
    for u in admins:
        pairs.append((u, u.profile.college))
    return pairs


def _render_digest(alerts):
    lines = []
    for a in alerts:
        scope = f"{a.college.code}" if a.college else '—'
        when = f"{a.month:02d}/{a.year}" if a.month and a.year else ''
        lines.append(
            f"[{LEVEL_LABELS.get(a.level, a.level).upper()}] {scope} · "
            f"{CATEGORY_LABELS.get(a.category, a.category)}{(' · ' + when) if when else ''}\n"
            f"  {a.title}\n  {a.message}")
    return '\n\n'.join(lines)


def send_alert_digest():
    """Email new unresolved alerts. Returns the number of emails sent."""
    unnotified = Alert.objects.filter(resolved=False, notified_at__isnull=True)
    if not unnotified.exists():
        return 0

    sent = 0
    emailed_ids = set()
    from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', 'no-reply@su-analytics.local')

    for user, college in _recipients():
        qs = unnotified.filter(college=college) if college else unnotified
        alerts = list(qs.select_related('college').order_by(
            'college__code', 'level', 'category'))
        if not alerts:
            continue
        body = (
            f"SU Analytics alert digest — {len(alerts)} new alert(s) "
            f"need attention.\n\n"
            + _render_digest(alerts)
            + "\n\nOpen the Alert Center in SU Analytics to resolve them.")
        try:
            from django.core.mail import send_mail
            send_mail(
                subject=f'SU Analytics — {len(alerts)} new alert(s)',
                message=body,
                from_email=from_email,
                recipient_list=[user.email],
                fail_silently=False,
            )
        except Exception:
            logger.exception('Alert digest delivery failed for %s', user.email)
            continue
        sent += 1
        emailed_ids.update(a.id for a in alerts)

    if emailed_ids:
        Alert.objects.filter(id__in=emailed_ids, notified_at__isnull=True).update(
            notified_at=timezone.now())
    return sent
