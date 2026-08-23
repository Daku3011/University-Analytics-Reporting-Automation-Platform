"""Template context: open alert counts for the sidebar/topbar (#6)."""
from django.db.models import Count, Q


def alert_counts(request):
    if not request.user.is_authenticated:
        return {}
    profile = getattr(request.user, 'profile', None)
    qs = None
    from analytics_app.models import Alert
    if profile and profile.role == 'super_admin':
        qs = Alert.objects.all()
    elif profile and profile.college_id:
        qs = Alert.objects.filter(college_id=profile.college_id)
    if qs is None:
        return {}
    agg = qs.filter(resolved=False).aggregate(
        total=Count('id'),
        critical=Count('id', filter=Q(level='critical')),
    )
    return {'alert_counts': agg}
