"""Automated alert detection engine (#6).

Three rules, all evaluated against institute-scope analytics rows
(department/programme breakdowns are drill-down detail and never trigger
college-level alerts):

- missing_data — elapsed months of the year with no college-scope row.
  warning; critical at ``missing_months_critical`` or more missing months.
- status — pending/incomplete rows left stale more than
  ``stale_pending_days`` past the month's end. warning.
- big_change — |month-over-month %| on views/reach/followers gained at or
  above ``big_change_pct``. warning; critical at 2x threshold. One alert per
  (college, year, month) listing every metric that crossed.

Every alert carries a stable ``dedup_key``: rescans upsert on it (refreshing
message/level and reopening an alert whose condition still holds) instead of
piling up duplicates. Open alerts whose condition no longer holds are
auto-resolved. Alerts without a dedup_key (created by hand in admin) are
never touched by the engine.
"""
from calendar import monthrange
from datetime import date

from django.conf import settings
from django.utils import timezone

from analytics_app.models import Alert, MonthlyAnalytics
from colleges.models import College

DEFAULT_ALERT_CONFIG = {
    'missing_months_critical': 3,
    'big_change_pct': 50,
    'stale_pending_days': 30,
}

# Metrics monitored for month-over-month swings, with display labels.
BIG_CHANGE_METRICS = [
    ('total_views', 'Total Views'),
    ('total_reach', 'Total Reach'),
    ('followers_gained', 'Followers Gained'),
]

MONTH_NAMES = dict(Alert._meta.get_field('month').choices)


def _config():
    cfg = dict(DEFAULT_ALERT_CONFIG)
    cfg.update(getattr(settings, 'ALERT_CONFIG', {}) or {})
    return cfg


def _upsert(dedup_key, defaults):
    """Create or refresh one alert. Returns (was_created, was_updated)."""
    existed = Alert.objects.filter(dedup_key=dedup_key).exists()
    _, created = Alert.objects.update_or_create(
        dedup_key=dedup_key,
        defaults={**defaults, 'resolved': False, 'resolved_at': None},
    )
    return created, (existed and not created)


def _missing_data_rule(college, year, elapsed_months):
    """One alert per college-year covering every month with no row yet."""
    if not elapsed_months:
        return 0, 0, set()
    existing = set(
        MonthlyAnalytics.objects.filter(
            college=college, year=year,
            department__isnull=True, programme__isnull=True,
            month__in=elapsed_months,
        ).values_list('month', flat=True))
    missing = [m for m in sorted(elapsed_months) if m not in existing]
    key = f'missing_data:{college.code}:{year}'
    if not missing:
        return 0, 0, set()

    level = 'critical' if len(missing) >= _config()['missing_months_critical'] else 'warning'
    names = ', '.join(MONTH_NAMES[m] for m in missing)
    created, updated = _upsert(key, {
        'college': college, 'category': 'missing_data', 'level': level,
        'title': f'{len(missing)} month(s) of {year} not submitted',
        'message': (
            f'No monthly analytics record for: {names}. '
            f'Institute-level totals for {year} stay incomplete until these are entered.'),
        'month': missing[-1], 'year': year,
    })
    return int(created), int(updated), {key}


def _status_rule(college, rows, today):
    """Stale pending/incomplete rows — one alert per college-month."""
    cfg = _config()
    created_count = updated_count = 0
    keys = set()
    for row in rows:
        month_end = date(row.year, row.month, monthrange(row.year, row.month)[1])
        days_late = (today - month_end).days
        if days_late <= cfg['stale_pending_days']:
            continue
        key = f'status:{college.code}:{row.year}:{row.month}'
        keys.add(key)
        created, updated = _upsert(key, {
            'college': college, 'category': 'status', 'level': 'warning',
            'title': f'{MONTH_NAMES[row.month]} {row.year} stuck as "{row.status}"',
            'message': (
                f'The {MONTH_NAMES[row.month]} {row.year} record has been '
                f'"{row.status}" for {days_late} days after month-end. '
                f'Review it — submit, verify, or mark incomplete as appropriate.'),
            'month': row.month, 'year': row.year,
        })
        created_count += int(created)
        updated_count += int(updated)
    return created_count, updated_count, keys


def _big_change_rule(college, rows_by_month, year):
    """MoM swings ≥ threshold — one combined alert per college-year-month."""
    cfg = _config()
    created_count = updated_count = 0
    keys = set()
    for month, cur in rows_by_month.items():
        prev = rows_by_month.get(month - 1)
        if prev is None:
            continue
        crossed = []
        worst = 0.0
        for field, label in BIG_CHANGE_METRICS:
            prev_val = getattr(prev, field) or 0
            cur_val = getattr(cur, field) or 0
            if not prev_val:
                continue  # no baseline to measure a swing against
            pct = abs((cur_val - prev_val) / prev_val * 100)
            direction = 'grew' if cur_val >= prev_val else 'dropped'
            if pct >= cfg['big_change_pct']:
                crossed.append(f'{label} {direction} {pct:.0f}%')
                worst = max(worst, pct)
        if not crossed:
            continue
        key = f'big_change:{college.code}:{year}:{month}'
        keys.add(key)
        level = 'critical' if worst >= 2 * cfg['big_change_pct'] else 'warning'
        created, updated = _upsert(key, {
            'college': college, 'category': 'big_change', 'level': level,
            'title': f'Sudden change in {MONTH_NAMES[month]} {year} numbers',
            'message': (
                f'Month-over-month swing vs {MONTH_NAMES[month - 1]}: '
                + '; '.join(crossed) + '. Verify the figures before they drive reports.'),
            'month': month, 'year': year,
        })
        created_count += int(created)
        updated_count += int(updated)
    return created_count, updated_count, keys


def run_alert_scan(year=None, today=None):
    """Scan every college and upsert alerts. Returns a summary dict.

    ``year``/``today`` default to the current local year/date; tests pass
    fixed values so results stay deterministic as real time moves on.
    """
    now_local = timezone.localtime(timezone.now())
    year = year or now_local.year
    today = today or now_local.date()

    # Months already over for the scanned year (future years have none).
    if year < today.year:
        elapsed = range(1, 13)
    elif year == today.year:
        elapsed = range(1, today.month + 1)
    else:
        elapsed = []

    created_count = updated_count = 0
    current_keys = set()

    for college in College.objects.all():
        rows = list(MonthlyAnalytics.objects.filter(
            college=college, year=year,
            department__isnull=True, programme__isnull=True,
        ).order_by('month'))

        created, updated_m, keys = _missing_data_rule(college, year, elapsed)
        created_count += created
        updated_count += updated_m
        current_keys |= keys

        created, updated_s, keys = _status_rule(college, [
            r for r in rows if r.status in ('pending', 'incomplete')], today)
        created_count += created
        updated_count += updated_s
        current_keys |= keys

        created, updated_b, keys = _big_change_rule(
            college, {r.month: r for r in rows}, year)
        created_count += created
        updated_count += updated_b
        current_keys |= keys

    # Auto-resolve: open scan-generated alerts whose condition is no longer
    # being raised this pass. Alerts from earlier years age out too — their
    # window is gone. Manual alerts (no key) are never touched.
    resolved_count = Alert.objects.filter(
        resolved=False, dedup_key__isnull=False,
    ).exclude(dedup_key__in=current_keys).update(
        resolved=True, resolved_at=timezone.now())

    return {
        'created': created_count,
        'updated': updated_count,
        'resolved': resolved_count,
        'open_total': Alert.objects.filter(resolved=False).count(),
        'year': year,
    }
