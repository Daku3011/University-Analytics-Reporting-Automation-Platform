import os
import json
import markdown
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.template.loader import render_to_string
from django.conf import settings
from django.core.cache import cache
# WeasyPrint requires system GTK/Pango libraries.
# Import lazily inside view functions so the app starts even if GTK isn't installed.
# See: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows
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
        if analytics:
            max_views = max(1, analytics.instagram_views, analytics.facebook_views, analytics.total_views)

        context = {
            'college': college,
            'month_name': month_name,
            'year': year,
            'analytics': analytics,
            'max_views': max_views,
            'events': events,
            'events_count': events.count(),
            'top_ig': top_ig,
            'top_fb': top_fb,
            'newspapers': newspapers,
            'press_releases': press_releases,
        }
        html_string = render_to_string('reports/monthly_report_template.html', context)
        from weasyprint import HTML  # lazy import — requires GTK/Pango on Windows
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

        # ── AI Summary via Gemini (gemini-api-dev skill) ──────────────────
        ai_summary = ""
        gemini_config = getattr(settings, 'GEMINI_CONFIG', {})
        model_name = gemini_config.get('MODEL', 'gemini-2.5-flash')
        cooldown_key = f"gemini_cooldown_{request.user.id}"
        limit_key = f"gemini_limit_{request.user.id}_{date.today()}"

        last_call = cache.get(cooldown_key)
        if last_call:
            ai_summary = ("<div style='display:flex;align-items:flex-start;gap:10px;padding:12px 16px;"
                          "background:#fdf2e6;border:1px solid #f0d4b0;border-radius:6px;'>"
                          "<i class='ph ph-clock' style='font-size:18px;color:#c97a2f;flex-shrink:0;margin-top:2px;'></i>"
                          "<div style='font-size:13.5px;color:#7a4a1a;'><strong>AI summary skipped</strong>"
                          " &mdash; Please wait 60 seconds before generating again.</div></div>")
        else:
            daily_count = cache.get(limit_key, 0)
            daily_limit = gemini_config.get('DAILY_LIMIT', 50)
            if daily_count >= daily_limit:
                ai_summary = ("<div style='display:flex;align-items:flex-start;gap:10px;padding:12px 16px;"
                              "background:#fbecea;border:1px solid #f0c8c5;border-radius:6px;'>"
                              "<i class='ph ph-warning-circle' style='font-size:18px;color:#b5534a;flex-shrink:0;margin-top:2px;'></i>"
                              f"<div style='font-size:13.5px;color:#7a2a22;'><strong>Daily limit reached</strong>"
                              f" &mdash; {daily_limit} AI summaries used today. Resets at midnight.</div></div>")
            else:
                try:
                    # New SDK: google-genai (replaces google-generativeai)
                    from google import genai
                    client = genai.Client(api_key=os.environ.get('GEMINI_API_KEY', ''))

                    prompt = f"""You are an analytics reporting assistant for Sarvajanik University.
Analyze the following social media quarterly data and write a professional narrative summary.

Quarter: Q{quarter} {year}
Months covered: {', '.join(month_names)}

Monthly breakdown:
{json.dumps(analytics_by_month, indent=2)}

Top Instagram posts (views/likes/shares):
{[{'views': p.views, 'likes': p.likes, 'shares': p.shares} for p in all_top_ig[:3]]}

Top Facebook posts (views/likes):
{[{'views': p.views, 'likes': p.likes} for p in all_top_fb[:3]]}

Write a structured professional quarterly summary with these sections:
1. Quarter Overview — overall performance highlights
2. Best Performing Month — which month and why
3. Platform Comparison — Instagram vs Facebook performance
4. Engagement Trends — follower growth patterns
5. Recommendations — 3 actionable recommendations for next quarter

Use clear professional language suitable for a university administration report."""

                    response = client.models.generate_content(
                        model=model_name,
                        contents=prompt,
                    )
                    raw_text = response.text

                    # Update rate-limit tracking
                    cooldown_secs = gemini_config.get('COOLDOWN_SECONDS', 60)
                    cache.set(cooldown_key, True, cooldown_secs)
                    cache.set(limit_key, daily_count + 1, 86400)

                    # Convert markdown → HTML
                    ai_summary = markdown.markdown(raw_text)

                except ImportError:
                    ai_summary = (
                        "<p class='ai-notice'>Install the new Gemini SDK: "
                        "<code>pip install google-genai</code></p>"
                    )
                except Exception as e:
                    ai_summary = f"<p class='ai-notice'>AI summary unavailable: {str(e)}</p>"

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
        from weasyprint import HTML  # lazy import — requires GTK/Pango on Windows
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
