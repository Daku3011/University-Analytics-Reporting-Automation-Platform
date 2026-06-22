import os
import json
import re
import time
from pathlib import Path
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from .models import MonthlyAnalytics, TopPost
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
    months = MonthlyAnalytics.MONTH_CHOICES
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
