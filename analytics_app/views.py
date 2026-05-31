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
                            'views': int(request.POST.get(f'top_{platform_key}_{i}_views', 0)),
                            'likes': int(request.POST.get(f'top_{platform_key}_{i}_likes', 0)),
                            'shares': int(request.POST.get(f'top_{platform_key}_{i}_shares', 0)),
                            'post_link': request.POST.get(f'top_{platform_key}_{i}_link', ''),
                        }
                    )

        return redirect('dashboard')
    colleges = College.objects.all()
    months = MonthlyAnalytics.MONTH_CHOICES
    return render(request, 'analytics_app/add_analytics.html', {'colleges': colleges, 'months': months})


@login_required
def extract_from_pdf(request):
    if request.method == 'POST':
        college_id = request.POST.get('college')
        month = int(request.POST.get('month'))
        year = int(request.POST.get('year'))
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

            # Read file and base64 encode
            with open(save_path, 'rb') as f:
                b64_data = base64.b64encode(f.read()).decode('utf-8')

            prompt = """You are a data extraction specialist for Sarvajanik University. Analyze the PDF and extract all social media analytics, events, and top posts data.

Extract the information and return ONLY valid JSON with this exact structure:
{
    "analytics": {
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
    },
    "top_posts": [
        {
            "platform": "instagram" or "facebook",
            "caption": "<post caption or description>",
            "views": <number or 0>,
            "likes": <number or 0>,
            "shares": <number or 0>,
            "post_link": "<URL if available, else empty string>"
        }
    ],
    "events": [
        {
            "title": "<event title>",
            "description": "<event description>",
            "category": "workshop/festival/placement/achievement/conference/guest_lecture/academic/cultural/sports/other",
            "date": "<YYYY-MM-DD>"
        }
    ]
}

Rules:
- Use 0 for any numeric field where data is not available.
- For events, map the category to the closest match from the allowed list.
- If no events are found, return an empty array.
- If no top posts are found, return an empty array.
- If no analytics data is found, return an empty object for analytics.
- Output ONLY valid JSON. No markdown, no code fences, no explanatory text."""

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

            # Store in session
            request.session['extracted_data'] = {
                'college_id': int(college_id),
                'month': month,
                'year': year,
                'analytics': extracted.get('analytics', {}),
                'top_posts': extracted.get('top_posts', []),
                'events': extracted.get('events', []),
            }
            request.session.modified = True

            return redirect('preview_extracted_data')

        except json.JSONDecodeError as e:
            messages.error(request, f'Failed to parse Gemini response as JSON: {e}')
        except Exception as e:
            messages.error(request, f'Extraction failed: {str(e)}')

        return redirect('extract_from_pdf')

    colleges = College.objects.all()
    months = MonthlyAnalytics.MONTH_CHOICES
    return render(request, 'analytics_app/extract_from_pdf.html', {
        'colleges': colleges,
        'months': months,
    })


@login_required
def preview_extracted_data(request):
    data = request.session.get('extracted_data')
    if not data:
        messages.warning(request, 'No extracted data found. Please upload a PDF first.')
        return redirect('extract_from_pdf')

    college = get_object_or_404(College, id=data['college_id'])

    if request.method == 'POST':
        month = data['month']
        year = data['year']

        # Save events
        for ev in data.get('events', []):
            Event.objects.create(
                college=college,
                title=ev.get('title', 'Untitled'),
                description=ev.get('description', ''),
                category=ev.get('category', 'other'),
                date=ev.get('date', f'{year}-{month:02d}-01'),
            )

        # Save analytics
        analytics_data = data.get('analytics', {})
        if analytics_data:
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

        # Save top posts
        for post in data.get('top_posts', []):
            TopPost.objects.create(
                college=college,
                month=month,
                year=year,
                platform=post.get('platform', 'instagram'),
                caption=post.get('caption', ''),
                views=int(post.get('views', 0)),
                likes=int(post.get('likes', 0)),
                shares=int(post.get('shares', 0)),
                post_link=post.get('post_link', ''),
            )

        # Clean up
        del request.session['extracted_data']

        messages.success(request, 'Data extracted from PDF has been saved successfully!')
        return redirect('dashboard')

    return render(request, 'analytics_app/preview_extracted_data.html', {
        'data': data,
        'college': college,
    })
