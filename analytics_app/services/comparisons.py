"""Comparison and trend computations for the Compare & Trends view (#3).

All aggregations operate on college-scope rows only (`department` and
`programme` NULL) so department/programme breakdown records never
double-count toward institute or university totals — same convention as
the submission status view.
"""
import json

from django.db.models import Sum

from analytics_app.models import ANALYSIS_METRIC_CHOICES, MonthlyAnalytics
from su_analytics.constants import MONTH_CHOICES

METRIC_KEYS = [key for key, _ in ANALYSIS_METRIC_CHOICES]
METRIC_LABELS = dict(ANALYSIS_METRIC_CHOICES)
DEFAULT_METRIC = 'total_views'

# College-level rows: no department/programme breakdown attached
COLLEGE_SCOPE_FILTERS = {'department__isnull': True, 'programme__isnull': True}


def pct_change(current, previous):
    """Percentage change from previous to current.

    Returns None when there is no meaningful baseline (previous is 0/None),
    so templates can render an em-dash instead of a misleading %.
    """
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _val(record, metric):
    """Safely read a metric field off a MonthlyAnalytics row."""
    return getattr(record, metric, 0) or 0


def build_yoy_comparison(college, year, metric=DEFAULT_METRIC):
    """Month-by-month comparison of `year` against `year - 1` for one college.

    Returns a dict with 12 month rows (current vs previous + % change), a
    per-metric summary table and Chart.js-ready JSON for the selected metric.
    """
    if metric not in METRIC_KEYS:
        metric = DEFAULT_METRIC
    prev_year = year - 1

    rows = MonthlyAnalytics.objects.filter(
        college=college, year__in=[year, prev_year], **COLLEGE_SCOPE_FILTERS,
    )
    cur_by_month = {r.month: r for r in rows if r.year == year}
    prev_by_month = {r.month: r for r in rows if r.year == prev_year}

    months = []
    chart_current, chart_previous, labels = [], [], []
    for m_num, m_label in MONTH_CHOICES:
        current = _val(cur_by_month.get(m_num), metric)
        previous = _val(prev_by_month.get(m_num), metric)
        months.append({
            'num': m_num,
            'label': m_label,
            'current': current,
            'previous': previous,
            'change': pct_change(current, previous),
        })
        labels.append(m_label[:3])
        chart_current.append(current)
        chart_previous.append(previous)

    # Per-metric year totals (sum over the already-fetched rows — no extra queries)
    metrics_summary = []
    for key in METRIC_KEYS:
        current = sum(_val(r, key) for r in cur_by_month.values())
        previous = sum(_val(r, key) for r in prev_by_month.values())
        metrics_summary.append({
            'key': key,
            'label': METRIC_LABELS[key],
            'current': current,
            'previous': previous,
            'change': pct_change(current, previous),
        })

    sel_summary = next(m for m in metrics_summary if m['key'] == metric)

    # Best month for the selected metric (None when the year has no data at all)
    best_row = max(months, key=lambda m: m['current']) if cur_by_month else None
    best_month = (
        {'label': best_row['label'], 'value': best_row['current']}
        if best_row and best_row['current'] > 0 else None
    )
    months_with_data = len(cur_by_month)

    return {
        'college': college,
        'year': year,
        'prev_year': prev_year,
        'selected_metric': metric,
        'selected_metric_label': METRIC_LABELS[metric],
        'months': months,
        'metrics_summary': metrics_summary,
        'selected_summary': sel_summary,
        'best_month': best_month,
        'months_with_data': months_with_data,
        'monthly_average': round(sel_summary['current'] / months_with_data) if months_with_data else 0,
        'chart_json': json.dumps({
            'labels': labels,
            'current': chart_current,
            'previous': chart_previous,
            'currentLabel': str(year),
            'previousLabel': str(prev_year),
        }),
    }


def build_institute_ranking(colleges, year, metric=DEFAULT_METRIC):
    """Rank colleges by a metric total for `year`, with YoY delta and share.

    Uses one grouped aggregation per year rather than per-college loops so
    the whole ranking costs two queries regardless of institute count.
    """
    if metric not in METRIC_KEYS:
        metric = DEFAULT_METRIC
    prev_year = year - 1
    college_ids = [c.id for c in colleges]

    def totals_for(target_year):
        qs = MonthlyAnalytics.objects.filter(
            year=target_year, college_id__in=college_ids, **COLLEGE_SCOPE_FILTERS,
        )
        return {
            row['college']: row['total'] or 0
            for row in qs.values('college').annotate(total=Sum(metric))
        }

    cur_totals = totals_for(year)
    prev_totals = totals_for(prev_year)

    rows = []
    for c in colleges:
        current = cur_totals.get(c.id, 0)
        rows.append({
            'college': c,
            'college_code': c.code,
            'college_name': c.name,
            'total': current,
            'previous': prev_totals.get(c.id, 0),
            'change': pct_change(current, prev_totals.get(c.id, 0)),
        })
    # Highest first; ties break alphabetically so ranks are stable
    rows.sort(key=lambda r: (-r['total'], r['college_name']))
    for i, r in enumerate(rows, start=1):
        r['rank'] = i

    university_total = sum(r['total'] for r in rows)
    previous_university_total = sum(r['previous'] for r in rows)
    for r in rows:
        r['share_pct'] = round(r['total'] / university_total * 100, 1) if university_total else 0.0

    top = next((r for r in rows if r['total'] > 0), None)

    return {
        'rows': rows,
        'metric': metric,
        'metric_label': METRIC_LABELS[metric],
        'year': year,
        'prev_year': prev_year,
        'university_total': university_total,
        'previous_university_total': previous_university_total,
        'university_change': pct_change(university_total, previous_university_total),
        'average': round(university_total / len(rows)) if rows else 0,
        'top_performer': top,
        'chart_json': json.dumps({
            'labels': [r['college_code'] for r in rows],
            'values': [r['total'] for r in rows],
        }),
    }
