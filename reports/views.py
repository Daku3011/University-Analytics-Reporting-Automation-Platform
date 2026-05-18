import os
import json
import markdown
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.conf import settings
from django.core.cache import cache
# WeasyPrint requires system GTK/Pango libraries.
# Import lazily inside view functions so the app starts even if GTK isn't installed.
# See: https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#windows
from colleges.models import College
from events.models import Event
from analytics_app.models import MonthlyAnalytics, TopPost
from .models import MonthlyReport, QuarterlyReport, NewspaperCoverage, PressRelease, UploadedDocumentReport


@login_required
def report_dashboard(request):
    monthly_reports = MonthlyReport.objects.select_related('college').all().order_by('-created_at')[:20]
    quarterly_reports = QuarterlyReport.objects.all().order_by('-created_at')[:10]
    doc_reports = UploadedDocumentReport.objects.all().order_by('-created_at')[:10]
    colleges = College.objects.all()
    months = range(1, 13)
    return render(request, 'reports/report_dashboard.html', {
        'monthly_reports': monthly_reports,
        'quarterly_reports': quarterly_reports,
        'doc_reports': doc_reports,
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


# ── New Feature: Upload 3 Monthly PDFs → Gemini Condenses → Quarterly PDF ─────

ALLOWED_EXTENSIONS = {'pdf'}   # Only PDF — Gemini natively understands PDF structure


def _save_uploaded_file(ufile, prefix):
    """Stream-save an uploaded file to disk without loading it all into memory."""
    import pathlib
    upload_dir = settings.MEDIA_ROOT / 'reports' / 'uploaded_sources'
    upload_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"{prefix}_{ufile.name.replace(' ', '_').replace('/', '_')}"
    save_path = upload_dir / safe_name
    with open(save_path, 'wb') as fout:
        for chunk in ufile.chunks(chunk_size=8 * 1024 * 1024):   # 8 MB chunks
            fout.write(chunk)
    return save_path, f'reports/uploaded_sources/{safe_name}'


def _gemini_upload_and_wait(client, file_path):
    """
    Upload a PDF to Gemini Files API directly from disk and wait until ACTIVE.
    Returns the uploaded file object ready to use in generate_content.
    """
    import time
    from google.genai import types as genai_types

    # Pass the string path directly so the SDK handles streaming and filename inference.
    # This prevents loading 70MB files entirely into RAM.
    uploaded = client.files.upload(
        file=str(file_path),
        config=genai_types.UploadFileConfig(
            mime_type='application/pdf',
            display_name=file_path.name
        )
    )

    # Poll until ACTIVE (large files can take 30-60 seconds)
    max_wait = 300   # 5 minutes max
    waited   = 0
    while uploaded.state.name == 'PROCESSING' and waited < max_wait:
        time.sleep(5)
        waited += 5
        uploaded = client.files.get(name=uploaded.name)

    if uploaded.state.name != 'ACTIVE':
        raise Exception(f"Gemini file processing failed or timed out for {file_path.name}. Final state: {uploaded.state.name}")

    return uploaded


@login_required
def upload_document_report(request):
    """
    Faculty uploads up to 3 monthly PDF reports (Jan + Feb + Mar, each up to 70 MB).
    Each PDF is saved to disk, uploaded to Gemini Files API, then Gemini reads all
    three and condenses them into a professional 3-month quarterly summary PDF.
    """
    if request.method != 'POST':
        return redirect('report_dashboard')

    title   = request.POST.get('doc_title', '').strip() or 'Uploaded Report'
    quarter = int(request.POST.get('doc_quarter', 1))
    year    = int(request.POST.get('doc_year', date.today().year))

    # ── DEBUG: print what Django received ─────────────────────────────────────
    print(f"[upload_document_report] request.FILES keys: {list(request.FILES.keys())}")
    print(f"[upload_document_report] request.POST keys:  {list(request.POST.keys())}")
    for k, f in request.FILES.items():
        print(f"  FILE '{k}': name={f.name!r}, size={f.size} bytes ({f.size/1024/1024:.1f} MB)")

    # ── Collect the uploaded files ────────────────────────────────────────────
    files_in = [
        request.FILES.get('source_file_1'),
        request.FILES.get('source_file_2'),
        request.FILES.get('source_file_3'),
    ]
    files_in = [f for f in files_in if f]   # drop any not uploaded

    if not files_in:
        messages.error(request,
            'No PDF files were received by the server. '
            'This usually means the files are too large (check DATA_UPLOAD_MAX_MEMORY_SIZE) '
            'or the form did not include the files. Please try again.')
        print("[upload_document_report] GUARD: files_in is empty — no files received")
        return redirect('report_dashboard')

    # Validate extensions
    for f in files_in:
        ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else ''
        if ext not in ALLOWED_EXTENSIONS:
            messages.error(request,
                f"File '{f.name}' is not a PDF. Only PDF files are supported. "
                f"Got extension: '{ext}' — allowed: {ALLOWED_EXTENSIONS}")
            print(f"[upload_document_report] GUARD: bad extension '{ext}' for file '{f.name}'")
            return redirect('report_dashboard')

    # ── Save each file to disk ────────────────────────────────────────────────
    saved_paths    = []   # pathlib.Path objects
    saved_relative = []   # 'reports/uploaded_sources/…' strings
    for i, ufile in enumerate(files_in, start=1):
        prefix = f"{year}_Q{quarter}_m{i}"
        path, rel = _save_uploaded_file(ufile, prefix)
        saved_paths.append(path)
        saved_relative.append(rel)

    quarter_label  = {1: 'January–March', 2: 'April–June',
                      3: 'July–September', 4: 'October–December'}.get(quarter, '')
    quarter_months = {1: ('January', 'February', 'March'),
                      2: ('April',   'May',      'June'),
                      3: ('July',    'August',   'September'),
                      4: ('October', 'November', 'December')}.get(quarter, ('Month 1', 'Month 2', 'Month 3'))

    # ── Dispatch Celery Task ──────────────────────────────────────────────────
    from .tasks import process_uploaded_document_report
    
    # We must pass serializable data (strings, ints, etc) to Celery
    saved_paths_str = [str(p) for p in saved_paths]
    
    task = process_uploaded_document_report.delay(
        title=title,
        quarter=quarter,
        year=year,
        uploaded_by_id=request.user.id,
        saved_paths=saved_paths_str,
        saved_relative=saved_relative,
        quarter_label=quarter_label,
        quarter_months=quarter_months
    )
    
    return redirect('document_report_processing', task_id=task.id)

@login_required
def document_report_processing(request, task_id):
    """View that shows a loading screen while Celery processes the report"""
    return render(request, 'reports/document_report_processing.html', {'task_id': task_id})

from django.http import JsonResponse
from celery.result import AsyncResult

@login_required
def check_task_status(request, task_id):
    """API endpoint for frontend to poll Celery task status"""
    task_result = AsyncResult(task_id)
    
    response_data = {
        'state': task_result.state,
        'message': 'Processing...'
    }
    
    if task_result.state == 'PROGRESS':
        response_data['message'] = task_result.info.get('message', 'Processing...')
    elif task_result.state == 'SUCCESS':
        response_data['message'] = 'Complete!'
        response_data.update(task_result.result) # Contains report_id and redirect_url
    elif task_result.state == 'FAILURE':
        response_data['message'] = 'An error occurred during generation.'
        response_data['error'] = str(task_result.info)
        
    return JsonResponse(response_data)


@login_required
def preview_document_report(request, report_id):
    report = get_object_or_404(UploadedDocumentReport, id=report_id)
    return render(request, 'reports/preview_document_report.html', {'report': report})

