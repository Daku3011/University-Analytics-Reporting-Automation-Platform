from django.db.models import Sum
from colleges.models import College
from analytics_app.models import MonthlyAnalytics, TopPost
from events.models import Event
from reports.models import NewspaperCoverage, ChannelCoverage, PressRelease

def get_yearly_data(college, year):
    """
    Fetches and aggregates all data sections for a specific college and year.
    
    Args:
        college (College): College instance.
        year (int): Year to filter.
        
    Returns:
        dict: Aggregated database objects.
    """
    # 1. Fetch monthly analytics for the year
    analytics = MonthlyAnalytics.objects.filter(college=college, year=year).order_by('month')
    
    # 2. Sum up total views, reach, etc.
    totals = analytics.aggregate(
        total_views=Sum('total_views'),
        total_reach=Sum('total_reach'),
        followers_gained=Sum('followers_gained'),
        reels_count=Sum('reels_count'),
        graphics_count=Sum('graphics_count')
    )
    
    # Guarantee numeric defaults instead of None
    for key in ['total_views', 'total_reach', 'followers_gained', 'reels_count', 'graphics_count']:
        if totals[key] is None:
            totals[key] = 0

    # 3. Fetch top posts
    top_posts = TopPost.objects.filter(college=college, year=year).order_by('month', '-views')

    # 4. Fetch events with preloaded media
    events = Event.objects.filter(college=college, date__year=year).order_by('-date').prefetch_related('media')

    # 5. Fetch publication/press coverages
    newspapers = NewspaperCoverage.objects.filter(college=college, year=year).order_by('-date')
    channels = ChannelCoverage.objects.filter(college=college, year=year).order_by('-month')
    press_releases = PressRelease.objects.filter(college=college, year=year).order_by('-date_submitted')

    return {
        'college': college,
        'year': year,
        'analytics': analytics,
        'totals': totals,
        'top_posts': top_posts,
        'events': events,
        'newspapers': newspapers,
        'channels': channels,
        'press_releases': press_releases,
    }
