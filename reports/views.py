import os, json, markdown
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.conf import settings
from weasyprint import HTML
from colleges.models import College
from events.models import Event
from analytics_app.models import MonthlyAnalytics, TopPost
from .models import MonthlyReport, QuarterlyReport, NewspaperCoverage, PressRelease

@login_required
def report_dashboard(request):
    monthly_reports = MonthlyReport.objects.select_related('college').all().order_by('-created_at')[:20]
    quarterly_reports = QuarterlyReport.objects.all().order_by('-created_at')[:10]
    colleges = College.objects.all()
    months = range(1, 13)
    return render(request, 'reports/report_dashboard.html', {
        'monthly_reports': monthly_reports,
        'quarterly_reports': quarterly_reports,
        'colleges': colleges,
        'months': months,
    })

@login_required
def generate_monthly(request):
    if request.method == 'POST':
        college_id = request.POST.get('college')
        month = int(request.POST['month'])
        year = int(request.POST['year'])
        if hasattr(request.user, 'profile') and request.user.profile.college:
            college = request.user.profile.college
        else:
            college = College.objects.get(id=college_id)
        analytics = MonthlyAnalytics.objects.filter(college=college, month=month, year=year).first()
        events = Event.objects.filter(college=college, date__month=month, date__year=year)
        top_ig = TopPost.objects.filter(college=college, month=month, year=year, platform='instagram')[:5]
        top_fb = TopPost.objects.filter(college=college, month=month, year=year, platform='facebook')[:5]
        newspapers = NewspaperCoverage.objects.filter(college=college, month=month, year=year)
        press_releases = PressRelease.objects.filter(college=college, month=month, year=year)

        month_name = date(year, month, 1).strftime('%B')

        max_views = 1
        for a_val in [analytics]:
            if a_val:
                max_views = max(max_views, a_val.instagram_views, a_val.facebook_views, a_val.total_views)

        context = {
            'college': college,
            'month_name': month_name,
            'year': year,
            'analytics': analytics,
            'max_views': max_views or 1,
            'events': events,
            'events_count': events.count(),
            'top_ig': top_ig,
            'top_fb': top_fb,
            'newspapers': newspapers,
            'press_releases': press_releases,
        }
        html_string = render_to_string('reports/monthly_report_template.html', context)
        pdf_dir = settings.MEDIA_ROOT / 'reports' / 'monthly'
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / f'{college.code}_{month}_{year}.pdf'
        HTML(string=html_string).write_pdf(pdf_path)

        report = MonthlyReport.objects.create(
            college=college, month=month, year=year,
            pdf_file=f'reports/monthly/{college.code}_{month}_{year}.pdf',
            generated_text=html_string
        )
        return redirect('preview_monthly', report_id=report.id)
    return redirect('report_dashboard')

@login_required
def preview_monthly(request, report_id):
    report = get_object_or_404(MonthlyReport, id=report_id)
    return render(request, 'reports/preview_monthly.html', {'report': report})

@login_required
def generate_quarterly(request):
    if request.method == 'POST':
        quarter = int(request.POST['quarter'])
        year = int(request.POST.get('year', 2026))
        start_month = {1: 1, 2: 4, 3: 7, 4: 10}[quarter]
        months_range = range(start_month, start_month + 3)
        month_names = [date(year, m, 1).strftime('%B') for m in months_range]

        all_analytics = MonthlyAnalytics.objects.filter(month__in=months_range, year=year)
        all_events = Event.objects.filter(date__month__in=months_range, date__year=year)
        all_top_ig = TopPost.objects.filter(month__in=months_range, year=year, platform='instagram').order_by('-views')[:5]
        all_top_fb = TopPost.objects.filter(month__in=months_range, year=year, platform='facebook').order_by('-views')[:5]
        all_newspapers = NewspaperCoverage.objects.filter(month__in=months_range, year=year)

        analytics_by_month = {}
        for m_num in months_range:
            m_name = date(year, m_num, 1).strftime('%B')
            qs = MonthlyAnalytics.objects.filter(month=m_num, year=year)
            analytics_by_month[m_name] = {
                'total_views': sum(a.total_views for a in qs),
                'total_reach': sum(a.total_reach for a in qs),
                'followers_gained': sum(a.followers_gained for a in qs),
                'instagram_views': sum(a.instagram_views for a in qs),
                'facebook_views': sum(a.facebook_views for a in qs),
            }

        # AI summary via Gemini with Rate Limiting
        ai_summary = ""
        from django.core.cache import cache
        from django.contrib import messages
        import time

        # Keys for tracking
        cooldown_key = f"gemini_cooldown_{request.user.id}"
        limit_key = f"gemini_limit_{request.user.id}_{date.today()}"
        
        # 1. Check Cooldown
        last_call = cache.get(cooldown_key)
        if last_call:
            ai_summary = "AI summary skipped due to cooldown. Please wait 60 seconds."
        else:
            # 2. Check Daily Limit
            daily_count = cache.get(limit_key, 0)
            if daily_count >= settings.GEMINI_CONFIG['DAILY_LIMIT']:
                ai_summary = f"AI summary skipped. Daily limit of {settings.GEMINI_CONFIG['DAILY_LIMIT']} reached."
            else:
                try:
                    import google.generativeai as genai
                    genai.configure(api_key=os.environ.get('GEMINI_API_KEY', ''))
                    model = genai.GenerativeModel('gemini-2.5-flash')
                    prompt = f"""Analyze the following university social media quarterly data and generate a professional summary.

Quarter: Q{quarter} {year}
Months: {', '.join(month_names)}

Monthly Analytics:
{json.dumps(analytics_by_month, indent=2)}

Top Instagram Posts: {[{'views': p.views, 'likes': p.likes, 'shares': p.shares} for p in all_top_ig[:3]]}
Top Facebook Posts: {[{'views': p.views, 'likes': p.likes} for p in all_top_fb[:3]]}

Write a professional quarterly summary with:
1. Best performing month
2. Platform comparison (Instagram vs Facebook)
3. Event impact highlights
4. Engagement trends
5. Recommendations for next quarter"""
                    response = model.generate_content(prompt)
                    ai_summary = response.text
                    
                    # 3. Update tracking on success
                    cache.set(cooldown_key, True, settings.GEMINI_CONFIG['COOLDOWN_SECONDS'])
                    cache.set(limit_key, daily_count + 1, 86400) # 24 hours
                    
                    # Convert markdown to HTML
                    ai_summary = markdown.markdown(ai_summary)
                    
                except Exception as e:
                    ai_summary = f"AI summary unavailable. Error: {str(e)}"

        totals = {}
        max_monthly_val = 1
        for key in ['total_views', 'total_reach', 'followers_gained', 'instagram_views', 'facebook_views']:
            totals[key] = sum(d.get(key, 0) for d in analytics_by_month.values())
            for m_name in month_names:
                val = analytics_by_month.get(m_name, {}).get(key, 0)
                if val > max_monthly_val:
                    max_monthly_val = val

        context = {
            'quarter': quarter,
            'year': year,
            'month_names': month_names,
            'analytics_by_month': analytics_by_month,
            'totals': totals,
            'max_monthly_val': max_monthly_val or 1,
            'all_top_ig': all_top_ig,
            'all_top_fb': all_top_fb,
            'ai_summary': ai_summary,
            'all_events_count': all_events.count(),
            'newspapers_count': all_newspapers.count(),
        }
        html_string = render_to_string('reports/quarterly_report_template.html', context)
        pdf_dir = settings.MEDIA_ROOT / 'reports' / 'quarterly'
        pdf_dir.mkdir(parents=True, exist_ok=True)
        pdf_path = pdf_dir / f'Q{quarter}_{year}.pdf'
        HTML(string=html_string).write_pdf(pdf_path)

        report = QuarterlyReport.objects.create(
            quarter=quarter, year=year,
            pdf_file=f'reports/quarterly/Q{quarter}_{year}.pdf',
            ai_summary=ai_summary
        )
        return redirect('preview_quarterly', report_id=report.id)
    return redirect('report_dashboard')

@login_required
def preview_quarterly(request, report_id):
    report = get_object_or_404(QuarterlyReport, id=report_id)
    return render(request, 'reports/preview_quarterly.html', {'report': report})
