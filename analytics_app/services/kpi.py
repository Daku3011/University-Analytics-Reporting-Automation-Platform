"""KPI gap computations shared by the KPI view and the portfolio report (#1)."""
from django.db.models import Sum

from analytics_app.models import KpiTarget, MonthlyAnalytics


def get_kpi_rows(college=None, year=None):
    """Actual-vs-target rows for one college — or every college when None.

    Actuals are aggregated at the same scope as the target (college /
    department / programme) for the target's year. Each row carries the
    college identity so callers can render single-college tables or group a
    university-wide roll-up by institute.
    """
    target_qs = KpiTarget.objects.select_related('department', 'programme', 'college')
    if college is not None:
        target_qs = target_qs.filter(college=college)
    if year is not None:
        target_qs = target_qs.filter(year=year)

    rows = []
    for t in target_qs:
        # Aggregate the actual metric value across the matching scope
        filters = {'college': t.college, 'year': t.year}
        if t.department_id:
            filters['department'] = t.department
        if t.programme_id:
            filters['programme'] = t.programme
        agg = MonthlyAnalytics.objects.filter(**filters).aggregate(total=Sum(t.metric))
        actual = agg['total'] or 0
        target_value = t.target_value
        gap = target_value - actual
        achievement = round((actual / target_value * 100), 1) if target_value else 0.0
        rows.append({
            'college': t.college,
            'college_code': t.college.code,
            'college_name': t.college.name,
            'scope': t.programme or t.department or t.college,
            'scope_type': 'Programme' if t.programme_id else (
                'Department' if t.department_id else 'College'),
            'metric': t.get_metric_display(),
            'metric_key': t.metric,
            'target': target_value,
            'actual': actual,
            'gap': gap,
            'achievement': achievement,
            'on_track': achievement >= 100,
        })
    return rows
