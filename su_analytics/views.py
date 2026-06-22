import json
import datetime
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.db.models import Sum
from events.models import Event
from analytics_app.models import MonthlyAnalytics
from colleges.models import College
from accounts.decorators import college_queryset_filter
from su_analytics.constants import MONTH_CHOICES


@login_required
def dashboard(request):
    # ── RBAC: scope data to user's college if not super admin ─────
    colleges = college_queryset_filter(College.objects.all(), request.user, college_field='pk')
    events = college_queryset_filter(Event.objects.all(), request.user)
    analytics = college_queryset_filter(MonthlyAnalytics.objects.all(), request.user)

    events_count = events.count()
    colleges_count = colleges.count()

    # ── ORM aggregation instead of loading all rows into Python ───
    totals = analytics.aggregate(
        total_views=Sum('total_views'),
        total_reach=Sum('total_reach'),
    )
    total_views = totals['total_views'] or 0
    total_reach = totals['total_reach'] or 0

    current_year = datetime.date.today().year
    monthly_data = (
        analytics
        .filter(year=current_year)
        .values('month')
        .annotate(
            views=Sum('total_views'),
            reach=Sum('total_reach'),
        )
        .order_by('month')
    )

    month_names = dict(MONTH_CHOICES)
    # Initialize all 12 months with 0 views and reach to show full year trend
    events_by_month = {name: {'views': 0, 'reach': 0} for _, name in MONTH_CHOICES}
    
    for row in monthly_data:
        m_label = month_names.get(row['month'], f"Month {row['month']}")
        if m_label in events_by_month:
            events_by_month[m_label] = {
                'views': row['views'] or 0,
                'reach': row['reach'] or 0,
            }

    chart_data = json.dumps({
        'labels': list(events_by_month.keys()),
        'views': [v['views'] for v in events_by_month.values()],
        'reach': [v['reach'] for v in events_by_month.values()],
    })

    recent_events = events.select_related('college').all()[:10]

    return render(request, 'dashboard.html', {
        'events_count': events_count,
        'colleges_count': colleges_count,
        'total_views': total_views,
        'total_reach': total_reach,
        'events_by_month': events_by_month,
        'chart_data': chart_data,
        'recent_events': recent_events,
    })
