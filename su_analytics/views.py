import json
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from events.models import Event
from analytics_app.models import MonthlyAnalytics
from colleges.models import College

@login_required
def dashboard(request):
    events_count = Event.objects.count()
    colleges_count = College.objects.count()
    analytics = MonthlyAnalytics.objects.all()
    total_views = sum(a.total_views for a in analytics)
    total_reach = sum(a.total_reach for a in analytics)
    events_by_month = {}
    for a in analytics:
        events_by_month[a.get_month_display()] = {
            'views': a.total_views,
            'reach': a.total_reach,
            'followers': a.followers_gained,
        }
    chart_data = json.dumps({
        'labels': list(events_by_month.keys()),
        'views': [v['views'] for v in events_by_month.values()],
        'reach': [v['reach'] for v in events_by_month.values()],
    })
    recent_events = Event.objects.select_related('college').all()[:10]
    return render(request, 'dashboard.html', {
        'events_count': events_count,
        'colleges_count': colleges_count,
        'total_views': total_views,
        'total_reach': total_reach,
        'events_by_month': events_by_month,
        'chart_data': chart_data,
        'recent_events': recent_events,
    })
