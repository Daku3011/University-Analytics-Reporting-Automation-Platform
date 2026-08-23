import os
import json
import re
import time
from pathlib import Path
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponseForbidden
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from accounts.decorators import role_required
from .models import MonthlyAnalytics, TopPost, STATUS_CHOICES
from colleges.models import College
from events.models import Event
from su_analytics.constants import MONTH_CHOICES


@login_required
def add_analytics(request):
    if request.method == 'POST':
        college_id = request.POST.get('college')
        month_str = request.POST.get('month', '')
        year_str = request.POST.get('year', '')

        # ── Input Validation ─────────────────────────────────────────
        if not month_str or not year_str:
            messages.error(request, 'Month and Year are required.')
            return redirect('add_analytics')

        try:
            month = int(month_str)
            year = int(year_str)
        except (ValueError, TypeError):
            messages.error(request, 'Month and Year must be valid numbers.')
            return redirect('add_analytics')

        if not (1 <= month <= 12):
            messages.error(request, 'Month must be between 1 and 12.')
            return redirect('add_analytics')

        # ── College Assignment (RBAC) ────────────────────────────────
        from accounts.decorators import get_user_college
        user_college = get_user_college(request.user)
        if user_college:
            college = user_college
        elif college_id:
            try:
                college = College.objects.get(id=college_id)
            except (College.DoesNotExist, ValueError):
                messages.error(request, 'Selected college does not exist.')
                return redirect('add_analytics')
        else:
            college = College.objects.first()
            if not college:
                messages.error(request, 'No colleges exist.')
                return redirect('add_analytics')

        def safe_int(val):
            """Safely convert POST value to int, defaulting to 0."""
            try:
                return int(val) if val else 0
            except (ValueError, TypeError):
                return 0

        data = {
            'instagram_views': safe_int(request.POST.get('instagram_views')),
            'facebook_views': safe_int(request.POST.get('facebook_views')),
            'total_views': safe_int(request.POST.get('total_views')),
            'instagram_reach': safe_int(request.POST.get('instagram_reach')),
            'facebook_reach': safe_int(request.POST.get('facebook_reach')),
            'total_reach': safe_int(request.POST.get('total_reach')),
            'instagram_followers': safe_int(request.POST.get('instagram_followers')),
            'facebook_followers': safe_int(request.POST.get('facebook_followers')),
            'youtube_subscribers': safe_int(request.POST.get('youtube_subscribers')),
            'followers_gained': safe_int(request.POST.get('followers_gained')),
            'reels_count': safe_int(request.POST.get('reels_count')),
            'graphics_count': safe_int(request.POST.get('graphics_count')),
        }
        MonthlyAnalytics.objects.update_or_create(
            college=college, month=month, year=year,
            defaults=data
        )

        # Save top posts
        for platform_key, platform_val in [('ig', 'instagram'), ('fb', 'facebook')]:
            for i in range(1, 3):
                caption = request.POST.get(f'top_{platform_key}_{i}_caption', '').strip()
                if caption:
                    TopPost.objects.update_or_create(
                        college=college, month=month, year=year,
                        platform=platform_val,
                        defaults={
                            'caption': caption,
                            'views': safe_int(request.POST.get(f'top_{platform_key}_{i}_views')),
                            'likes': safe_int(request.POST.get(f'top_{platform_key}_{i}_likes')),
                            'shares': safe_int(request.POST.get(f'top_{platform_key}_{i}_shares')),
                            'post_link': request.POST.get(f'top_{platform_key}_{i}_link', ''),
                        }
                    )

        messages.success(request, f'Analytics for {college.code} — {date(year, month, 1).strftime("%B %Y")} saved.')
        return redirect('dashboard')

    # GET: show form, scoped by RBAC
    from accounts.decorators import get_user_college
    user_college = get_user_college(request.user)
    if user_college:
        colleges = College.objects.filter(id=user_college.id)
    else:
        colleges = College.objects.all()
    months = MONTH_CHOICES
    return render(request, 'analytics_app/add_analytics.html', {'colleges': colleges, 'months': months})



@login_required
def extract_from_pdf(request):
    if request.method == 'POST':
        pdf_file = request.FILES.get('pdf_file')

        if not pdf_file:
            messages.error(request, 'Please upload a PDF file.')
            return redirect('extract_from_pdf')

        ext = pdf_file.name.rsplit('.', 1)[-1].lower() if '.' in pdf_file.name else ''
        if ext != 'pdf':
            messages.error(request, 'Only PDF files are supported.')
            return redirect('extract_from_pdf')

        # Save to disk
        upload_dir = settings.MEDIA_ROOT / 'temp_extracts'
        upload_dir.mkdir(parents=True, exist_ok=True)
        safe_name = f"extract_{request.user.id}_{pdf_file.name.replace(' ', '_').replace('/', '_')}"
        save_path = upload_dir / safe_name
        with open(save_path, 'wb') as fout:
            for chunk in pdf_file.chunks(chunk_size=8 * 1024 * 1024):
                fout.write(chunk)

        import base64

        try:
            from google import genai
            from google.genai import types as genai_types

            api_key = os.environ.get('GEMINI_API_KEY', '')
            if not api_key:
                raise Exception('GEMINI_API_KEY not set in environment.')

            model_name = getattr(settings, 'GEMINI_CONFIG', {}).get('MODEL', 'gemini-2.5-flash')

            client = genai.Client(api_key=api_key)

            with open(save_path, 'rb') as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')

            college_list = list(College.objects.all().values('id', 'name', 'code'))
            college_names_str = '", "'.join(f'{c["name"]} (code: {c["code"]})' for c in college_list)

            prompt = f'''You are a data extraction specialist for Sarvajanik University. Analyze the PDF and extract data.

First, identify which college this document belongs to from the list below:
"{college_names_str}"

Also identify the month (as a number 1-12) and year.

Then extract all social media analytics, events, and top posts.

Return ONLY valid JSON with this exact structure:
{{
    "college_name": "<exact college name from the list or empty string if unsure>",
    "month": <month number 1-12 or 0>,
    "year": <year number or 0>,
    "analytics": {{
        "instagram_views": <number or 0>,
        "facebook_views": <number or 0>,
        "total_views": <number or 0>,
        "instagram_reach": <number or 0>,
        "facebook_reach": <number or 0>,
        "total_reach": <number or 0>,
        "instagram_followers": <number or 0>,
        "facebook_followers": <number or 0>,
        "youtube_subscribers": <number or 0>,
        "followers_gained": <number or 0>,
        "reels_count": <number or 0>,
        "graphics_count": <number or 0>
    }},
    "top_posts": [
        {{
            "platform": "instagram" or "facebook",
            "caption": "<post caption or description>",
            "views": <number or 0>,
            "likes": <number or 0>,
            "shares": <number or 0>,
            "post_link": "<URL if available, else empty string>"
        }}
    ],
    "events": [
        {{
            "title": "<event title>",
            "description": "<event description>",
            "category": "workshop/festival/placement/achievement/conference/guest_lecture/academic/cultural/sports/other",
            "date": "<YYYY-MM-DD>"
        }}
    ]
}}

Rules:
- college_name must be EXACTLY one of the provided names or empty string.
- month must be a number 1-12 (January=1, February=2, etc.) or 0 if unknown.
- Use 0 for any missing numeric field.
- Map event categories to the closest match from the allowed list.
- Empty arrays if nothing found. Empty object for analytics if no data.
- Output ONLY valid JSON. No markdown, no code fences, no explanatory text.'''

            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=[
                        genai_types.Part(inline_data=genai_types.Blob(mime_type='application/pdf', data=b64_data)),
                        genai_types.Part(text=prompt),
                    ],
                )
            except Exception as exc:
                if 'INVALID_ARGUMENT' in str(exc) or '400' in str(exc):
                    print(f"[extract_from_pdf] {model_name} failed. Retrying with gemini-2.5-pro...")
                    response = client.models.generate_content(
                        model="gemini-2.5-pro",
                        contents=[
                            genai_types.Part(inline_data=genai_types.Blob(mime_type='application/pdf', data=b64_data)),
                            genai_types.Part(text=prompt),
                        ],
                    )
                else:
                    raise

            raw_text = response.text.strip()

            json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', raw_text)
            if json_match:
                raw_text = json_match.group(1).strip()

            extracted = json.loads(raw_text)

            try:
                os.remove(save_path)
            except Exception:
                pass

            # Match extracted college name to DB
            detected_college_name = extracted.get('college_name', '')
            college = None
            if detected_college_name:
                college = College.objects.filter(name__iexact=detected_college_name.strip()).first()
                if not college:
                    college = College.objects.filter(name__icontains=detected_college_name.strip()).first()

            month = int(extracted.get('month', 0)) or 0
            year = int(extracted.get('year', 0)) or 0

            # Store in session
            request.session['extracted_data'] = {
                'detected_college_id': college.id if college else None,
                'detected_college_name': college.name if college else (detected_college_name or ''),
                'month': month,
                'year': year,
                'analytics': extracted.get('analytics', {}),
                'top_posts': extracted.get('top_posts', []),
                'events': extracted.get('events', []),
            }
            request.session.modified = True

            if not college:
                messages.warning(request, 'Could not determine the college from the PDF. Please select one manually on the next screen.')

            return redirect('preview_extracted_data')

        except json.JSONDecodeError as e:
            messages.error(request, f'Failed to parse Gemini response as JSON: {e}')
        except Exception as e:
            messages.error(request, f'Extraction failed: {str(e)}')

        return redirect('extract_from_pdf')

    return render(request, 'analytics_app/extract_from_pdf.html')


@login_required
def preview_extracted_data(request):
    data = request.session.get('extracted_data')
    if not data:
        messages.warning(request, 'No extracted data found. Please upload a PDF first.')
        return redirect('extract_from_pdf')

    colleges = College.objects.all()
    months = MONTH_CHOICES
    current_year = date.today().year

    college_id = data.get('detected_college_id')
    college = College.objects.filter(id=college_id).first() if college_id else None
    month = data.get('month', 0)
    year = data.get('year', 0)

    if request.method == 'POST':
        college_id = request.POST.get('college')
        month = int(request.POST.get('month', 0))
        year = int(request.POST.get('year', 0))
        college = get_object_or_404(College, id=college_id)

        for ev in data.get('events', []):
            Event.objects.create(
                college=college,
                title=ev.get('title', 'Untitled'),
                description=ev.get('description', ''),
                category=ev.get('category', 'other'),
                date=ev.get('date', f'{year}-{month:02d}-01') if month and year else f'{current_year}-01-01',
            )

        analytics_data = data.get('analytics', {})
        if analytics_data and month and year:
            MonthlyAnalytics.objects.update_or_create(
                college=college, month=month, year=year,
                defaults={
                    'instagram_views': int(analytics_data.get('instagram_views', 0)),
                    'facebook_views': int(analytics_data.get('facebook_views', 0)),
                    'total_views': int(analytics_data.get('total_views', 0)),
                    'instagram_reach': int(analytics_data.get('instagram_reach', 0)),
                    'facebook_reach': int(analytics_data.get('facebook_reach', 0)),
                    'total_reach': int(analytics_data.get('total_reach', 0)),
                    'instagram_followers': int(analytics_data.get('instagram_followers', 0)),
                    'facebook_followers': int(analytics_data.get('facebook_followers', 0)),
                    'youtube_subscribers': int(analytics_data.get('youtube_subscribers', 0)),
                    'followers_gained': int(analytics_data.get('followers_gained', 0)),
                    'reels_count': int(analytics_data.get('reels_count', 0)),
                    'graphics_count': int(analytics_data.get('graphics_count', 0)),
                }
            )

        for post in data.get('top_posts', []):
            TopPost.objects.create(
                college=college,
                month=month or 1,
                year=year or current_year,
                platform=post.get('platform', 'instagram'),
                caption=post.get('caption', ''),
                views=int(post.get('views', 0)),
                likes=int(post.get('likes', 0)),
                shares=int(post.get('shares', 0)),
                post_link=post.get('post_link', ''),
            )

        del request.session['extracted_data']

        messages.success(request, 'Data extracted from PDF has been saved successfully!')
        return redirect('dashboard')

    return render(request, 'analytics_app/preview_extracted_data.html', {
        'data': data,
        'college': college,
        'colleges': colleges,
        'months': months,
        'current_year': current_year,
    })


@login_required
def yearly_overview(request):
    # 1. RBAC college filtering
    from accounts.decorators import get_user_college, college_queryset_filter
    colleges = college_queryset_filter(College.objects.all(), request.user, college_field='pk')
    
    # 2. Get available years in DB
    from django.utils import timezone
    from reports.models import NewspaperCoverage, PressRelease
    current_year = timezone.now().year
    
    # Get distinct years
    years_set = set(
        list(MonthlyAnalytics.objects.values_list('year', flat=True).distinct()) +
        list(Event.objects.values_list('date__year', flat=True).distinct()) +
        list(NewspaperCoverage.objects.values_list('year', flat=True).distinct()) +
        list(PressRelease.objects.values_list('year', flat=True).distinct())
    )
    years_set.add(current_year)
    years = sorted(list(years_set), reverse=True)
    
    # 3. Determine selected college
    user_college = get_user_college(request.user)
    if user_college:
        selected_college = user_college
    else:
        college_id = request.GET.get('college')
        if college_id:
            selected_college = get_object_or_404(colleges, id=college_id)
        else:
            selected_college = colleges.first()
            
    # 4. Determine selected year
    year_str = request.GET.get('year')
    if year_str:
        try:
            selected_year = int(year_str)
        except ValueError:
            selected_year = current_year
    else:
        selected_year = current_year
        
    # 5. Fetch yearly data if college exists
    yearly_data = {}
    chart_data = "{}"
    if selected_college:
        from analytics_app.services.yearly_data import get_yearly_data
        yearly_data = get_yearly_data(selected_college, selected_year)
        
        # Prepare monthly views & reach chart data
        # Initialize all 12 months
        monthly_stats = {name: {'views': 0, 'reach': 0} for _, name in MONTH_CHOICES}
        month_names = dict(MONTH_CHOICES)
        
        for item in yearly_data['analytics']:
            m_name = month_names.get(item.month)
            if m_name in monthly_stats:
                monthly_stats[m_name]['views'] = item.total_views
                monthly_stats[m_name]['reach'] = item.total_reach
                
        chart_data = json.dumps({
            'labels': list(monthly_stats.keys()),
            'views': [v['views'] for v in monthly_stats.values()],
            'reach': [v['reach'] for v in monthly_stats.values()],
        })

    # ── Submission status summary (#2) ──────────────────────────────
    profile = getattr(request.user, 'profile', None)
    can_manage_status = request.user.is_superuser or (profile and profile.role in ('super_admin', 'college_admin'))
    status_summary = []
    if selected_college:
        from django.db.models import Count
        counts = {
            row['status']: row['c']
            for row in MonthlyAnalytics.objects.filter(college=selected_college, year=selected_year)
            .values('status').annotate(c=Count('id'))
        }
        for s_val, s_label in STATUS_CHOICES:
            status_summary.append((s_val, s_label, counts.get(s_val, 0)))

    return render(request, 'analytics_app/yearly_overview.html', {
        'colleges': colleges if not user_college else None,  # Hide selector if locked to single college
        'years': years,
        'selected_college': selected_college,
        'selected_year': selected_year,
        'yearly_data': yearly_data,
        'chart_data': chart_data,
        'month_choices': MONTH_CHOICES,
        'status_summary': status_summary,
        'status_choices': STATUS_CHOICES,
        'can_manage_status': can_manage_status,
    })


@role_required('super_admin', 'college_admin')
def update_status(request, pk):
    """Update the submission status of a monthly analytics record (#2)."""
    from accounts.decorators import get_user_college
    from django.utils import timezone

    record = get_object_or_404(MonthlyAnalytics, pk=pk)

    # College admins may only manage records for their own college
    user_college = get_user_college(request.user)
    if user_college and record.college_id != user_college.id:
        return HttpResponseForbidden(
            '<h2>403 Forbidden</h2><p>You can only manage records for your own college.</p>'
        )

    if request.method == 'POST':
        new_status = request.POST.get('status')
        valid = dict(STATUS_CHOICES)
        if new_status in valid:
            record.status = new_status
            now = timezone.now()
            if new_status == 'submitted':
                record.submitted_by = request.user
                record.submitted_at = now
            elif new_status == 'verified':
                record.verified_by = request.user
                record.verified_at = now
            record.save()
            messages.success(
                request,
                f'Status for {record.college.code} — {record.get_month_display()} {record.year} '
                f'set to {valid[new_status]}.'
            )
        else:
            messages.error(request, 'Invalid status value.')

    params = []
    if not user_college:
        params.append(f'college={record.college_id}')
    params.append(f'year={record.year}')
    return redirect('yearly_overview' + ('?' + '&'.join(params) if params else ''))


@login_required
def kpi_gap_view(request):
    """Consolidated KPI/targets gap view: actual vs target per KPI (#1)."""
    from accounts.decorators import get_user_college, college_queryset_filter
    from django.db.models import Sum
    from django.utils import timezone

    colleges = college_queryset_filter(College.objects.all(), request.user, college_field='pk')
    current_year = timezone.now().year

    user_college = get_user_college(request.user)

    # Years available from targets + analytics
    years_set = set(
        list(KpiTarget.objects.values_list('year', flat=True).distinct()) +
        list(MonthlyAnalytics.objects.values_list('year', flat=True).distinct())
    )
    years_set.add(current_year)
    years = sorted(list(years_set), reverse=True)

    # Selected college (college_admin locked to own college)
    if user_college:
        selected_college = user_college
    else:
        college_id = request.GET.get('college')
        selected_college = (
            get_object_or_404(colleges, id=college_id) if college_id
            else colleges.first()
        )

    # Selected year
    year_str = request.GET.get('year')
    try:
        selected_year = int(year_str) if year_str else current_year
    except ValueError:
        selected_year = current_year

    rows = []
    if selected_college:
        targets = KpiTarget.objects.filter(
            college=selected_college, year=selected_year
        ).select_related('department', 'programme', 'college')

        for t in targets:
            # Aggregate the actual metric value across the matching scope
            filters = {'college': selected_college, 'year': selected_year}
            if t.department_id:
                filters['department'] = t.department
            if t.programme_id:
                filters['programme'] = t.programme
            agg = MonthlyAnalytics.objects.filter(**filters).aggregate(
                total=Sum(t.metric)
            )
            actual = agg['total'] or 0
            target_value = t.target_value
            gap = target_value - actual
            achievement = round((actual / target_value * 100), 1) if target_value else 0.0
            rows.append({
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

    total = len(rows)
    on_track = sum(1 for r in rows if r['on_track'])
    behind = total - on_track

    context = {
        'colleges': colleges,
        'selected_college': selected_college,
        'can_select_college': not bool(user_college),
        'years': years,
        'selected_year': selected_year,
        'rows': rows,
        'total': total,
        'on_track': on_track,
        'behind': behind,
    }
    return render(request, 'analytics_app/kpi_gap.html', context)


@login_required
def submission_status(request):
    """Submission status indicators across the year (#2).

    Shows, per month, the college-level submission status (pending / submitted /
    incomplete / verified) plus who submitted/verified and when. Missing months
    are surfaced explicitly so gaps are visible at a glance.
    """
    from accounts.decorators import get_user_college, college_queryset_filter
    from django.utils import timezone

    user_college = get_user_college(request.user)
    colleges = college_queryset_filter(College.objects.all(), request.user, college_field='pk')
    current_year = timezone.now().year

    years_set = set(MonthlyAnalytics.objects.values_list('year', flat=True).distinct())
    years_set.add(current_year)
    years = sorted(list(years_set), reverse=True)

    if user_college:
        selected_college = user_college
    else:
        college_id = request.GET.get('college')
        selected_college = (
            get_object_or_404(colleges, id=college_id) if college_id
            else colleges.first()
        )

    year_str = request.GET.get('year')
    try:
        selected_year = int(year_str) if year_str else current_year
    except ValueError:
        selected_year = current_year

    records = {}
    if selected_college:
        qs = MonthlyAnalytics.objects.filter(
            college=selected_college, year=selected_year,
            department__isnull=True, programme__isnull=True,
        ).select_related('submitted_by', 'verified_by')
        for rec in qs:
            records[rec.month] = rec

    status_order = [s[0] for s in STATUS_CHOICES]
    status_counts = {s[0]: 0 for s in STATUS_CHOICES}
    status_counts['missing'] = 0

    months = []
    for m_num, m_label in MONTH_CHOICES:
        rec = records.get(m_num)
        if rec:
            status_counts[rec.status] += 1
            months.append({
                'num': m_num,
                'label': m_label,
                'status': rec.status,
                'status_label': rec.get_status_display(),
                'submitted_by': rec.submitted_by.get_full_name() or rec.submitted_by.username if rec.submitted_by else '—',
                'submitted_at': rec.submitted_at.strftime('%d %b %Y, %H:%M') if rec.submitted_at else '—',
                'verified_by': rec.verified_by.get_full_name() or rec.verified_by.username if rec.verified_by else '—',
                'pk': rec.pk,
            })
        else:
            status_counts['missing'] += 1
            months.append({
                'num': m_num,
                'label': m_label,
                'status': 'missing',
                'status_label': 'Not Submitted',
                'submitted_by': '—',
                'submitted_at': '—',
                'verified_by': '—',
                'pk': None,
            })

    context = {
        'colleges': colleges,
        'selected_college': selected_college,
        'can_select_college': not bool(user_college),
        'years': years,
        'selected_year': selected_year,
        'months': months,
        'status_counts': status_counts,
        'status_order': status_order,
    }
    return render(request, 'analytics_app/submission_status.html', context)
