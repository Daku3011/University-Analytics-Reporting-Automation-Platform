from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required
from .models import MonthlyAnalytics
from colleges.models import College

@login_required
def add_analytics(request):
    if request.method == 'POST':
        college_id = request.POST.get('college')
        month = int(request.POST['month'])
        year = int(request.POST['year'])
        if hasattr(request.user, 'profile') and request.user.profile.college:
            college = request.user.profile.college
        else:
            college = College.objects.get(id=college_id) if college_id else College.objects.first()
        data = {
            'instagram_views': request.POST.get('instagram_views', 0),
            'facebook_views': request.POST.get('facebook_views', 0),
            'total_views': request.POST.get('total_views', 0),
            'instagram_reach': request.POST.get('instagram_reach', 0),
            'facebook_reach': request.POST.get('facebook_reach', 0),
            'total_reach': request.POST.get('total_reach', 0),
            'instagram_followers': request.POST.get('instagram_followers', 0),
            'facebook_followers': request.POST.get('facebook_followers', 0),
            'youtube_subscribers': request.POST.get('youtube_subscribers', 0),
            'followers_gained': request.POST.get('followers_gained', 0),
            'reels_count': request.POST.get('reels_count', 0),
            'graphics_count': request.POST.get('graphics_count', 0),
        }
        MonthlyAnalytics.objects.update_or_create(
            college=college, month=month, year=year,
            defaults={k: int(v) for k, v in data.items()}
        )
        return redirect('dashboard')
    colleges = College.objects.all()
    months = MonthlyAnalytics.MONTH_CHOICES
    return render(request, 'analytics_app/add_analytics.html', {'colleges': colleges, 'months': months})
