import re
import markdown
from datetime import date
from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.conf import settings

from colleges.models import College
from events.models import Event
from analytics_app.models import MonthlyAnalytics, TopPost
from reports.models import NewspaperCoverage, PressRelease
from reports.services.gemini_service import GeminiService
from reports.services.rate_limit_service import RateLimitService

@login_required
def compare_reports(request):
    """
    Compare two months side-by-side with AI-powered honest assessment.
    GET shows the form. POST fetches data and runs Gemini comparison.
    """
    colleges = College.objects.all()
    months = range(1, 13)

    if request.method != 'POST':
        return render(request, 'reports/compare_reports.html', {
            'colleges': colleges,
            'months': months,
            'comparison_html': None,
        })

    college_id = request.POST.get('college')
    month_a_str = request.POST.get('month_a')
    month_b_str = request.POST.get('month_b')
    year_str = request.POST.get('year')

    if not college_id or not month_a_str or not month_b_str:
        error_html = (
            "<div style='display:flex;align-items:flex-start;gap:10px;padding:12px 16px;"
            "background:#fbecea;border:1px solid #f0c8c5;border-radius:6px;'>"
            "<i class='ph ph-warning-circle' style='font-size:18px;color:#b5534a;flex-shrink:0;margin-top:2px;'></i>"
            "<div style='font-size:13.5px;color:#7a2a22;'><strong>Error</strong> &mdash; Missing required fields for comparison.</div></div>"
        )
        return render(request, 'reports/compare_reports.html', {
            'colleges': colleges,
            'months': months,
            'comparison_html': error_html,
        })

    try:
        month_a = int(month_a_str)
        month_b = int(month_b_str)
        year = int(year_str) if year_str else date.today().year
    except ValueError:
        error_html = (
            "<div style='display:flex;align-items:flex-start;gap:10px;padding:12px 16px;"
            "background:#fbecea;border:1px solid #f0c8c5;border-radius:6px;'>"
            "<i class='ph ph-warning-circle' style='font-size:18px;color:#b5534a;flex-shrink:0;margin-top:2px;'></i>"
            "<div style='font-size:13.5px;color:#7a2a22;'><strong>Error</strong> &mdash; Month and Year must be valid numeric values.</div></div>"
        )
        return render(request, 'reports/compare_reports.html', {
            'colleges': colleges,
            'months': months,
            'comparison_html': error_html,
        })

    if not (1 <= month_a <= 12) or not (1 <= month_b <= 12):
        error_html = (
            "<div style='display:flex;align-items:flex-start;gap:10px;padding:12px 16px;"
            "background:#fbecea;border:1px solid #f0c8c5;border-radius:6px;'>"
            "<i class='ph ph-warning-circle' style='font-size:18px;color:#b5534a;flex-shrink:0;margin-top:2px;'></i>"
            "<div style='font-size:13.5px;color:#7a2a22;'><strong>Error</strong> &mdash; Months must be between 1 and 12.</div></div>"
        )
        return render(request, 'reports/compare_reports.html', {
            'colleges': colleges,
            'months': months,
            'comparison_html': error_html,
        })

    try:
        college = College.objects.get(id=college_id)
    except (College.DoesNotExist, ValueError):
        error_html = (
            "<div style='display:flex;align-items:flex-start;gap:10px;padding:12px 16px;"
            "background:#fbecea;border:1px solid #f0c8c5;border-radius:6px;'>"
            "<i class='ph ph-warning-circle' style='font-size:18px;color:#b5534a;flex-shrink:0;margin-top:2px;'></i>"
            "<div style='font-size:13.5px;color:#7a2a22;'><strong>Error</strong> &mdash; Specified College does not exist.</div></div>"
        )
        return render(request, 'reports/compare_reports.html', {
            'colleges': colleges,
            'months': months,
            'comparison_html': error_html,
        })

    try:
        month_a_name = date(year, month_a, 1).strftime('%B')
        month_b_name = date(year, month_b, 1).strftime('%B')
    except ValueError:
        error_html = (
            "<div style='display:flex;align-items:flex-start;gap:10px;padding:12px 16px;"
            "background:#fbecea;border:1px solid #f0c8c5;border-radius:6px;'>"
            "<i class='ph ph-warning-circle' style='font-size:18px;color:#b5534a;flex-shrink:0;margin-top:2px;'></i>"
            "<div style='font-size:13.5px;color:#7a2a22;'><strong>Error</strong> &mdash; Invalid Year value specified.</div></div>"
        )
        return render(request, 'reports/compare_reports.html', {
            'colleges': colleges,
            'months': months,
            'comparison_html': error_html,
        })

    # Fetch data for both months
    analytics_a = MonthlyAnalytics.objects.filter(college=college, month=month_a, year=year).first()
    analytics_b = MonthlyAnalytics.objects.filter(college=college, month=month_b, year=year).first()

    events_a = Event.objects.filter(college=college, date__month=month_a, date__year=year)
    events_b = Event.objects.filter(college=college, date__month=month_b, date__year=year)

    top_ig_a = TopPost.objects.filter(college=college, month=month_a, year=year, platform='instagram')[:5]
    top_ig_b = TopPost.objects.filter(college=college, month=month_b, year=year, platform='instagram')[:5]
    top_fb_a = TopPost.objects.filter(college=college, month=month_a, year=year, platform='facebook')[:5]
    top_fb_b = TopPost.objects.filter(college=college, month=month_b, year=year, platform='facebook')[:5]

    newspapers_a = NewspaperCoverage.objects.filter(college=college, month=month_a, year=year)
    newspapers_b = NewspaperCoverage.objects.filter(college=college, month=month_b, year=year)

    press_a = PressRelease.objects.filter(college=college, month=month_a, year=year)
    press_b = PressRelease.objects.filter(college=college, month=month_b, year=year)

    # Structure data for Gemini
    def analytics_dict(a):
        if not a:
            return {'total_views': 0, 'total_reach': 0, 'followers_gained': 0,
                    'instagram_views': 0, 'facebook_views': 0,
                    'instagram_reach': 0, 'facebook_reach': 0,
                    'reels_count': 0, 'graphics_count': 0, 'youtube_subscribers': 0}
        return {
            'total_views': a.total_views, 'total_reach': a.total_reach,
            'followers_gained': a.followers_gained,
            'instagram_views': a.instagram_views, 'facebook_views': a.facebook_views,
            'instagram_reach': a.instagram_reach, 'facebook_reach': a.facebook_reach,
            'reels_count': a.reels_count, 'graphics_count': a.graphics_count,
            'youtube_subscribers': a.youtube_subscribers,
        }

    d_a = analytics_dict(analytics_a)
    d_b = analytics_dict(analytics_b)

    events_data_a = [{'title': e.title, 'category': e.get_category_display(), 'date': str(e.date)} for e in events_a]
    events_data_b = [{'title': e.title, 'category': e.get_category_display(), 'date': str(e.date)} for e in events_b]

    top_ig_data_a = [{'views': p.views, 'likes': p.likes, 'shares': p.shares} for p in top_ig_a]
    top_ig_data_b = [{'views': p.views, 'likes': p.likes, 'shares': p.shares} for p in top_ig_b]
    top_fb_data_a = [{'views': p.views, 'likes': p.likes} for p in top_fb_a]
    top_fb_data_b = [{'views': p.views, 'likes': p.likes} for p in top_fb_b]

    news_count_a = newspapers_a.count()
    news_count_b = newspapers_b.count()
    press_count_a = press_a.count()
    press_count_b = press_b.count()

    # ── Gemini Comparison ──
    is_limited, limit_error = RateLimitService.check_rate_limit(request.user.id)
    if is_limited:
        comparison_html = limit_error
    else:
        try:
            prompt = f"""You are a brutally honest data analyst for Sarvajanik University. No sugar coating. No corporate fluff. Just direct truth.

Compare the following two months of social media analytics, events, and media coverage for {college.name}.

MONTH A: {month_a_name} {year}
{d_a}

Events ({len(events_data_a)}):
{events_data_a}

Top Instagram posts:
{top_ig_data_a}

Top Facebook posts:
{top_fb_data_a}

Newspaper coverage: {news_count_a}
Press releases: {press_count_a}


MONTH B: {month_b_name} {year}
{d_b}

Events ({len(events_data_b)}):
{events_data_b}

Top Instagram posts:
{top_ig_data_b}

Top Facebook posts:
{top_fb_data_b}

Newspaper coverage: {news_count_b}
Press releases: {press_count_b}


Write a brutally honest month-over-month comparison in clean HTML. Use <h2>, <h3>, <p>, <ul>, <li>, <strong>, <table>, <tr>, <th>, <td> tags. Output ONLY valid HTML — no markdown.

Structure:

<h2>1. The Verdict — Which Month Was Better?</h2>
<p>One direct sentence stating definitively which month performed better overall and why.</p>

<h2>2. Numbers Don't Lie — Key Metrics Head-to-Head</h2>
<p>A <table> comparing specific metrics side by side: total views, total reach, followers gained, reels count, graphics count. Include a column for % change. If the change is negative, say it explicitly in red.</p>

<h2>3. Social Media — What Worked, What Tanked</h2>
<p>Compare Instagram vs Facebook performance across both months. Which platform improved, which declined. Be specific about numbers.</p>
<p>Compare top posts: was engagement up or down? Did content quality improve?</p>

<h2>4. Events — Were We Active or Slacking?</h2>
<p>Compare event counts and types. Which month had more events? Better variety? More impactful categories?</p>

<h2>5. Media & Press Coverage</h2>
<p>Compare newspaper coverage and press release output. Did visibility improve?</p>

<h2>6. What Needs to Change — Honest Recommendations</h2>
<ul>
<li>3-5 specific, actionable recommendations. Not generic advice. Numbers-driven. Example: "Instagram views dropped from {d_a['instagram_views']} to {d_b['instagram_views']} — need to increase reel output from {d_a['reels_count']} to at least 8 per month."</li>
<li>If a metric declined, say what must be done to recover it.</li>
<li>If a metric improved, explain what to keep doing.</li>
</ul>"""

            raw = GeminiService.generate_content(prompt)

            # Fallback: convert markdown bold to HTML
            raw = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', raw)
            # Fallback: convert markdown to HTML if no HTML tags present
            if '<h2>' not in raw and '<p>' not in raw:
                raw = markdown.markdown(raw, extensions=['extra'])
            comparison_html = raw

            # Record success and set cooldown
            RateLimitService.record_success(request.user.id)

        except Exception as e:
            comparison_html = f"<p style='color:#b91c1c;'>AI comparison unavailable: {str(e)}</p>"

    return render(request, 'reports/compare_reports.html', {
        'colleges': colleges,
        'months': months,
        'comparison_html': comparison_html,
        'college': college,
        'month_a_name': month_a_name,
        'month_b_name': month_b_name,
        'year': year,
        'd_a': d_a,
        'd_b': d_b,
        'events_a': events_a,
        'events_b': events_b,
        'top_ig_a': top_ig_a,
        'top_ig_b': top_ig_b,
        'top_fb_a': top_fb_a,
        'top_fb_b': top_fb_b,
        'newspapers_a': newspapers_a,
        'newspapers_b': newspapers_b,
        'press_a': press_a,
        'press_b': press_b,
        'events_a_count': events_a.count(),
        'events_b_count': events_b.count(),
        'news_a_count': news_count_a,
        'news_b_count': news_count_b,
        'press_a_count': press_count_a,
        'press_b_count': press_count_b,
    })
