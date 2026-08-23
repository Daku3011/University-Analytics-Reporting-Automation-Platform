"""Annual Portfolio Report (#5): one consolidated per-college-per-year document.

Stateless by design — every chapter regenerates on demand from a single
`build_portfolio_context(college, year)` call that all three exporters
(PDF / Excel / Word) and the preview page consume.
"""
from collections import Counter
from django.db.models import Sum

from analytics_app.models import MonthlyAnalytics
from analytics_app.services.kpi import get_kpi_rows
from analytics_app.services.yearly_data import get_yearly_data
from analytics_app.services.comparisons import pct_change
from su_analytics.constants import MONTH_CHOICES


def _monthly_totals(college, year):
    """Institute-scope monthly sums for one year (dept/prog rows excluded)."""
    agg = MonthlyAnalytics.objects.filter(
        college=college, year=year, department__isnull=True, programme__isnull=True,
    ).aggregate(
        total_views=Sum('total_views'), total_reach=Sum('total_reach'),
        followers_gained=Sum('followers_gained'),
        reels_count=Sum('reels_count'), graphics_count=Sum('graphics_count'),
    )
    return {key: value or 0 for key, value in agg.items()}


def build_portfolio_context(college, year):
    """Assemble every chapter of the annual portfolio for `college` in `year`."""
    data = get_yearly_data(college, year)
    totals = _monthly_totals(college, year)
    prev_totals = _monthly_totals(college, year - 1)

    # ── Chapter 1: Executive summary ────────────────────────────────
    metrics = ['total_views', 'total_reach', 'followers_gained', 'reels_count', 'graphics_count']
    yoy = [{
        'label': label,
        'current': totals[key],
        'previous': prev_totals[key],
        'change': pct_change(totals[key], prev_totals[key]),
    } for key, label in [
        ('total_views', 'Total Views'), ('total_reach', 'Total Reach'),
        ('followers_gained', 'Followers Gained'), ('reels_count', 'Reels Published'),
        ('graphics_count', 'Graphics Published'),
    ]]

    kpi_rows = get_kpi_rows(college=college, year=year)
    if kpi_rows:
        avg_attainment = round(sum(r['achievement'] for r in kpi_rows) / len(kpi_rows))
        targets_met = sum(1 for r in kpi_rows if r['on_track'])
    else:
        avg_attainment = None
        targets_met = 0

    executive_summary = {
        'year': year,
        'prev_year': year - 1,
        'yoy': yoy,
        'event_count': data['events'].count(),
        'press_release_count': data['press_releases'].count(),
        'media_count': data['newspapers'].count() + data['channels'].count(),
        'top_post_count': data['top_posts'].count(),
        'kpi_avg_attainment': avg_attainment,
        'kpi_targets_met': targets_met,
        'kpi_target_count': len(kpi_rows),
        'months_reported': MonthlyAnalytics.objects.filter(
            college=college, year=year, department__isnull=True, programme__isnull=True,
        ).values_list('month', flat=True).distinct().count(),
    }

    # ── Chapter 2: Social media (month-by-month table) ──────────────
    by_month = {rec.month: rec for rec in data['analytics']}
    monthly_rows = [{
        'num': num,
        'label': label,
        'record': by_month.get(num),
    } for num, label in MONTH_CHOICES]
    monthly_rows = [row for row in monthly_rows if row['record'] is not None]

    social_media = {
        'totals': totals,
        'monthly': monthly_rows,
        'top_posts': list(data['top_posts']),
        # Peak single-month views — used to scale the print bar chart
        'max_month_views': max(
            (row['record'].total_views or 0 for row in monthly_rows), default=0),
    }

    # ── Chapter 3: Events (+ category counts) ───────────────────────
    events = list(data['events'])
    category_counts = Counter(e.category or 'other' for e in events)
    events_chapter = {
        'events': events,
        'total': len(events),
        'categories': sorted(category_counts.items(), key=lambda kv: (-kv[1], kv[0])),
    }

    # ── Chapter 4: Media coverage (newspapers + channels) ───────────
    newspapers = list(data['newspapers'])
    channels = list(data['channels'])
    media_chapter = {
        'newspapers': newspapers,
        'channels': channels,
        'total': len(newspapers) + len(channels),
    }

    # ── Chapter 5: Press releases (+ placements/reach) ─────────────
    press = list(data['press_releases'])
    press_chapter = {
        'releases': press,
        'total': len(press),
        'total_placements': sum(p.placements or 0 for p in press),
    }

    return {
        'college': college,
        'college_name': college.name,
        'college_code': college.code,
        'generated_note': f'Compiled from SU Analytics · {college.code} · Annual Portfolio',
        'chapters': {
            'executive_summary': executive_summary,
            'social_media': social_media,
            'events': events_chapter,
            'media_coverage': media_chapter,
            'press_releases': press_chapter,
            'kpi_performance': {'rows': kpi_rows},
        },
    }
