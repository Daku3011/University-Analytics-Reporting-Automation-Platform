import json
import markdown
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.conf import settings

from events.models import Event
from analytics_app.models import MonthlyAnalytics, TopPost
from reports.models import QuarterlyReport, NewspaperCoverage, PressRelease
from reports.services.pdf_service import PDFService
from reports.services.gemini_service import GeminiService
from reports.services.rate_limit_service import RateLimitService
from su_analytics.constants import ANALYTICS_KEYS

@login_required
def generate_quarterly(request):
    if request.method == 'POST':
        quarter_str = request.POST.get('quarter')
        year_str = request.POST.get('year')
        
        if not quarter_str:
            messages.error(request, "Missing quarter parameter.")
            return redirect('report_dashboard')

        try:
            quarter = int(quarter_str)
            year = int(year_str) if year_str else date.today().year
        except ValueError:
            messages.error(request, "Quarter and Year must be valid numeric values.")
            return redirect('report_dashboard')

        if quarter not in [1, 2, 3, 4]:
            messages.error(request, "Quarter must be between 1 and 4.")
            return redirect('report_dashboard')

        start_month = {1: 1, 2: 4, 3: 7, 4: 10}[quarter]
        months_range = range(start_month, start_month + 3)
        try:
            month_names = [date(year, m, 1).strftime('%B') for m in months_range]
        except ValueError:
            messages.error(request, "Invalid Year value specified.")
            return redirect('report_dashboard')

        all_analytics = MonthlyAnalytics.objects.filter(month__in=months_range, year=year)
        all_events = Event.objects.filter(date__month__in=months_range, date__year=year)
        all_top_ig = TopPost.objects.filter(month__in=months_range, year=year, platform='instagram').order_by('-views')[:5]
        all_top_fb = TopPost.objects.filter(month__in=months_range, year=year, platform='facebook').order_by('-views')[:5]
        all_newspapers = NewspaperCoverage.objects.filter(month__in=months_range, year=year)
        all_press_releases = PressRelease.objects.filter(month__in=months_range, year=year)

        def _monthly_dict(qs):
            return {
                'total_views': sum(a.total_views for a in qs),
                'total_reach': sum(a.total_reach for a in qs),
                'followers_gained': sum(a.followers_gained for a in qs),
                'instagram_views': sum(a.instagram_views for a in qs),
                'facebook_views': sum(a.facebook_views for a in qs),
                'instagram_reach': sum(a.instagram_reach for a in qs),
                'facebook_reach': sum(a.facebook_reach for a in qs),
                'reels_count': sum(a.reels_count for a in qs),
                'graphics_count': sum(a.graphics_count for a in qs),
                'youtube_subscribers': sum(a.youtube_subscribers for a in qs),
                'instagram_followers': sum(a.instagram_followers for a in qs),
                'facebook_followers': sum(a.facebook_followers for a in qs),
            }

        analytics_by_month = {}
        for m_num in months_range:
            m_name = date(year, m_num, 1).strftime('%B')
            analytics_by_month[m_name] = _monthly_dict(
                MonthlyAnalytics.objects.filter(month=m_num, year=year)
            )

        # ── Year-over-Year Comparison (same quarter, previous year) ───────
        prev_year = year - 1
        prev_analytics_by_month = {}
        for m_num in months_range:
            m_name = date(prev_year, m_num, 1).strftime('%B')
            prev_analytics_by_month[m_name] = _monthly_dict(
                MonthlyAnalytics.objects.filter(month=m_num, year=prev_year)
            )

        prev_all_events = Event.objects.filter(date__month__in=months_range, date__year=prev_year)
        prev_all_newspapers = NewspaperCoverage.objects.filter(month__in=months_range, year=prev_year)
        prev_all_press_releases = PressRelease.objects.filter(month__in=months_range, year=prev_year)
        prev_top_ig = TopPost.objects.filter(month__in=months_range, year=prev_year, platform='instagram').order_by('-views')[:5]
        prev_top_fb = TopPost.objects.filter(month__in=months_range, year=prev_year, platform='facebook').order_by('-views')[:5]

        comparison = {}
        for key in ANALYTICS_KEYS:
            curr_val = sum(d.get(key, 0) for d in analytics_by_month.values())
            prev_val = sum(d.get(key, 0) for d in prev_analytics_by_month.values())
            diff = curr_val - prev_val
            pct = ((diff / prev_val) * 100) if prev_val else None
            comparison[key] = {
                'current': curr_val,
                'previous': prev_val,
                'diff': diff,
                'pct': pct,
            }

        comparison['events_count'] = {
            'current': all_events.count(),
            'previous': prev_all_events.count(),
            'diff': all_events.count() - prev_all_events.count(),
            'pct': None,
        }
        comparison['newspapers_count'] = {
            'current': all_newspapers.count(),
            'previous': prev_all_newspapers.count(),
            'diff': all_newspapers.count() - prev_all_newspapers.count(),
            'pct': None,
        }
        comparison['press_releases_count'] = {
            'current': all_press_releases.count(),
            'previous': prev_all_press_releases.count(),
            'diff': all_press_releases.count() - prev_all_press_releases.count(),
            'pct': None,
        }

        # ── AI Summary via Gemini (gemini-api-dev skill) ──────────────────
        is_limited, limit_error = RateLimitService.check_rate_limit(request.user.id)
        if is_limited:
            ai_summary = limit_error
        else:
            try:
                prev_monthly_breakdown = {m: prev_analytics_by_month[m] for m in month_names if m in prev_analytics_by_month}

                def summarize_posts(posts):
                    return [{'views': p.views, 'likes': p.likes, 'shares': getattr(p, 'shares', 0)} for p in posts[:3]]

                prompt = f"""You are a brutally honest data analyst for Sarvajanik University. No sugar coating, no corporate fluff.

Analyze the following quarterly data and write a direct, honest assessment covering social media, events, media coverage, and press activity.

Quarter: Q{quarter} {year}
Months covered: {', '.join(month_names)}

Monthly social media breakdown (current year):
{json.dumps(analytics_by_month, indent=2)}

Year-over-Year Comparison (Q{quarter} {year} vs Q{quarter} {prev_year}):
{json.dumps(comparison, indent=2)}

Monthly breakdown (previous year — Q{quarter} {prev_year}):
{json.dumps(prev_monthly_breakdown, indent=2)}

Top Instagram posts (current year):
{summarize_posts(all_top_ig)}

Top Instagram posts (previous year):
{summarize_posts(prev_top_ig)}

Top Facebook posts (current year):
{summarize_posts(all_top_fb)}

Top Facebook posts (previous year):
{summarize_posts(prev_top_fb)}

Events count — {year}: {all_events.count()}, {prev_year}: {prev_all_events.count()}
Newspaper coverage — {year}: {all_newspapers.count()}, {prev_year}: {prev_all_newspapers.count()}
Press releases — {year}: {all_press_releases.count()}, {prev_year}: {prev_all_press_releases.count()}

Write a structured quarterly summary in clean HTML (use <h2>, <h3>, <p>, <ul>, <li>, <strong>) with these sections:

<h2>1. Quarter Overview</h2>
<p>One paragraph: the honest truth about how this quarter went. What worked. What didn't. Cover social media, events, and media presence.</p>

<h2>2. Year-over-Year Comparison — Q{quarter} {year} vs Q{quarter} {prev_year}</h2>
<p>Compare this quarter's performance against the same quarter last year across ALL areas: social media metrics (views, reach, followers), content output (reels, graphics), events, newspaper coverage, and press releases. Which metrics improved, which declined, and by how much. Be brutally honest — if numbers dropped, say so. If they grew, acknowledge it.</p>

<h2>3. Best vs Worst Month</h2>
<p>Which month was strongest, which was weakest, and why. Be specific with numbers from social media AND events.</p>

<h2>4. Platform Comparison — Instagram vs Facebook</h2>
<p>Which platform delivered and which underperformed. Compare views, reach, engagement. Tell the truth about where effort is wasted.</p>

<h2>5. Events, Media &amp; Press Activity</h2>
<p>Compare event counts and categories between months. Is newspaper coverage improving? Are press releases generating placements? Connect activity levels to social media performance.</p>

<h2>6. Engagement &amp; Content Trends</h2>
<p>Is follower growth healthy or stagnant? Are reels getting views? Are graphics worth the effort? Compare reels and graphics output between months and years.</p>

<h2>7. What Must Change — Honest Recommendations</h2>
<ul>
<li>3-5 specific, actionable recommendations covering social media AND events/media. Not generic. Example: "Instagram Reels views dropped X% — need minimum Y reels/month."</li>
<li>Call out specific weaknesses. If something is working, say what to keep doing.</li>
<li>If events or media coverage declined, recommend how to recover them.</li>
</ul>

Output ONLY valid HTML. Use <strong> for emphasis."""

                raw_text = GeminiService.generate_content(prompt)
                
                # Update rate limit tracker
                RateLimitService.record_success(request.user.id)

                # Convert markdown → HTML
                ai_summary = markdown.markdown(raw_text)

            except Exception as e:
                ai_summary = f"<p class='ai-notice'>AI summary unavailable: {str(e)}</p>"

        totals = {}
        max_monthly_val = 1
        for key in ANALYTICS_KEYS:
            totals[key] = sum(d.get(key, 0) for d in analytics_by_month.values())
            for m_name in month_names:
                val = analytics_by_month.get(m_name, {}).get(key, 0)
                if val > max_monthly_val:
                    max_monthly_val = val

        context = {
            'quarter': quarter,
            'year': year,
            'prev_year': prev_year,
            'month_names': month_names,
            'analytics_by_month': analytics_by_month,
            'prev_analytics_by_month': prev_analytics_by_month,
            'comparison': comparison,
            'totals': totals,
            'prev_totals': {k: v['previous'] for k, v in comparison.items()},
            'max_monthly_val': max_monthly_val or 1,
            'all_top_ig': all_top_ig,
            'all_top_fb': all_top_fb,
            'prev_top_ig': prev_top_ig,
            'prev_top_fb': prev_top_fb,
            'ai_summary': ai_summary,
            'all_events_count': all_events.count(),
            'all_prev_events_count': prev_all_events.count(),
            'newspapers_count': all_newspapers.count(),
            'prev_newspapers_count': prev_all_newspapers.count(),
            'press_releases_count': all_press_releases.count(),
            'prev_press_releases_count': prev_all_press_releases.count(),
        }
        html_string = render_to_string('reports/quarterly_report_template.html', context)
        
        try:
            pdf_path = settings.MEDIA_ROOT / 'reports' / 'quarterly' / f'Q{quarter}_{year}.pdf'
            PDFService.compile_html_to_pdf(html_string, pdf_path)
        except Exception as e:
            messages.error(request, f"PDF compilation failed: {str(e)}")
            return redirect('report_dashboard')

        report, _created = QuarterlyReport.objects.update_or_create(
            quarter=quarter, year=year,
            defaults={
                'pdf_file': f'reports/quarterly/Q{quarter}_{year}.pdf',
                'ai_summary': ai_summary,
            }
        )
        return redirect('preview_quarterly', report_id=report.id)
    return redirect('report_dashboard')


@login_required
def preview_quarterly(request, report_id):
    report = get_object_or_404(QuarterlyReport, id=report_id)
    return render(request, 'reports/preview_quarterly.html', {'report': report})
