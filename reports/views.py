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

    # ── Gemini Files API: upload each PDF & wait for ACTIVE ──────────────────
    quarter_label  = {1: 'January–March', 2: 'April–June',
                      3: 'July–September', 4: 'October–December'}.get(quarter, '')
    quarter_months = {1: ('January', 'February', 'March'),
                      2: ('April',   'May',      'June'),
                      3: ('July',    'August',   'September'),
                      4: ('October', 'November', 'December')}.get(quarter, ('Month 1', 'Month 2', 'Month 3'))

    ai_summary      = ''
    gemini_config   = getattr(settings, 'GEMINI_CONFIG', {})
    model_name      = gemini_config.get('MODEL', 'gemini-2.5-flash')
    api_key         = os.environ.get('GEMINI_API_KEY', '')
    uploaded_gemini = []   # keep references for cleanup

    try:
        from google import genai
        from google.genai import types as genai_types
        client = genai.Client(api_key=api_key)

        extracted_data_list = []
        
        # Helper to split large PDFs before sending to Gemini
        def split_pdf_if_needed(fpath, max_size_mb=20):
            import os
            file_size_mb = os.path.getsize(fpath) / (1024 * 1024)
            if file_size_mb <= max_size_mb:
                return [fpath]
            
            try:
                from pypdf import PdfReader, PdfWriter
                from pathlib import Path
            except ImportError:
                print("[upload_document_report] pypdf not installed, cannot split. It may fail.")
                return [fpath]
                
            print(f"[upload_document_report] Splitting {fpath.name} ({file_size_mb:.1f}MB) into chunks...")
            reader = PdfReader(fpath)
            total_pages = len(reader.pages)
            num_chunks = int((file_size_mb // max_size_mb) + 1)
            pages_per_chunk = (total_pages // num_chunks) + 1
            
            chunk_paths = []
            for j in range(num_chunks):
                writer = PdfWriter()
                start_page = j * pages_per_chunk
                end_page = min((j + 1) * pages_per_chunk, total_pages)
                
                if start_page >= total_pages:
                    break
                    
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])
                    
                chunk_path = Path(fpath).parent / f"{fpath.stem}_chunk{j+1}.pdf"
                with open(chunk_path, "wb") as f_out:
                    writer.write(f_out)
                chunk_paths.append(chunk_path)
            return chunk_paths
        
        # ── Map Phase: Extract JSON data from each file individually ──
        for i, fpath in enumerate(saved_paths):
            print(f"[upload_document_report] Processing {fpath.name}...")
            chunk_paths = split_pdf_if_needed(fpath)
            
            uploaded_gfiles = []
            for chunk_path in chunk_paths:
                print(f"[upload_document_report] Uploading {chunk_path.name} to Gemini...")
                gfile = _gemini_upload_and_wait(client, chunk_path)
                uploaded_gfiles.append(gfile)
            
            try:
                print(f"[upload_document_report] Extracting JSON data from {fpath.name}...")
                month_name = quarter_months[i] if i < len(quarter_months) else f"Month {i+1}"
                map_prompt = f"""Extract the core metrics and activities from this monthly report for {month_name} {year}. 
Please output a strict JSON object detailing:
- "month": "{month_name}"
- "executive_summary": A brief 1-2 sentence highlight.
- "social_metrics": object with total_reach, total_views, followers_gained.
- "top_posts": array of objects (date, platform, topic, reach).
- "events": array of objects (date, name, attendance, impact).
- "media_coverage": object (total_placements, total_reach, key_mentions).
- "press_releases": total count.
- "takeaways": array of bullet points."""
                
                try:
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=uploaded_gfiles + [map_prompt]
                    )
                except Exception as map_exc:
                    if 'INVALID_ARGUMENT' in str(map_exc) or '400' in str(map_exc):
                        print(f"[upload_document_report] {model_name} failed with INVALID_ARGUMENT for {fpath.name}. Retrying with gemini-2.5-pro...")
                        try:
                            resp = client.models.generate_content(
                                model="gemini-2.5-pro",
                                contents=uploaded_gfiles + [map_prompt]
                            )
                        except Exception as inner_exc:
                            print(f"[upload_document_report] Fallback to gemini-2.5-pro also failed: {inner_exc}")
                            raise inner_exc
                    else:
                        raise map_exc
                extracted_data_list.append(resp.text)
                print(f"[upload_document_report] Successfully extracted data for {month_name}.")
                
            except Exception as e:
                print(f"[upload_document_report] CRITICAL WARNING: Could not extract data from {fpath.name}. Skipping this month. Error: {e}")
                # Inject a safe placeholder so the entire report doesn't crash
                extracted_data_list.append(f"""{{
                    "month": "{month_name}",
                    "executive_summary": "Data could not be automatically extracted for this month due to document complexity limits.",
                    "social_metrics": {{"total_reach": 0, "total_views": 0, "followers_gained": 0}},
                    "top_posts": [],
                    "events": [],
                    "media_coverage": {{"total_placements": 0, "total_reach": 0, "key_mentions": []}},
                    "press_releases": 0,
                    "takeaways": ["Please review this month manually as the AI encountered an extraction error."]
                }}""")
            finally:
                # Immediate cleanup to save Gemini storage quota and bypass 3,600 page limits
                for uf in uploaded_gfiles:
                    try:
                        client.files.delete(name=uf.name)
                        print(f"[upload_document_report] Deleted {uf.name} from Gemini.")
                    except Exception as cleanup_exc:
                        print(f"[upload_document_report] Cleanup warning for {uf.name}: {cleanup_exc}")

        # Build month list for the prompt
        months_uploaded = ', '.join(quarter_months[:len(saved_paths)])
        
        # Combine all extracted JSON into a single text block
        combined_json_text = "\n\n".join([f"--- Data Extract {i+1} ---\n{data}" for i, data in enumerate(extracted_data_list)])

        # ── Reduce Phase: Generate final HTML report from the consolidated JSON ──
        prompt = f"""You are an expert data analyst and report designer for Sarvajanik University.
The following JSON data represents the extracted metrics and activities for the months of {months_uploaded} {year}.

RAW EXTRACTED DATA:
{combined_json_text}

Your task: Produce a highly visual, professional **{quarter_label} Quarterly Summary Report** in clean HTML.
DO NOT JUST WRITE LONG TEXT. You must use data visualization (SVG), metric cards, and data tables to summarize the data.

You must exclusively output HTML using these specific CSS classes which are already defined:
- `<div class="metric-grid">` containing `<div class="metric-card"><div class="metric-value">X</div><div class="metric-label">Y</div></div>`
- `<div class="chart-container">` containing raw, well-formatted `<svg>` code for charts.
- Standard `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` for tabular data.
- `<div class="highlight-quote">` for important text highlights, quotes, or overarching quarter themes.

Structure your response exactly into these sections:

<h2>1. Executive Overview</h2>
- Start with a `<div class="highlight-quote">` highlighting the quarter's most impressive overarching achievement.
- Follow with a `<div class="metric-grid">` showing 3-4 top-level aggregate metrics for the quarter (e.g., Total Reach, Total Events, New Followers, Total PR).

<h2>2. Social Media Performance</h2>
- Use metric cards for platform-specific stats (Instagram, Facebook, YouTube).
- Create a beautiful **inline SVG bar chart** or **pie chart** comparing the reach, views, or follower growth across different platforms. Make the SVG clean, using #4f46e5 and #7c3aed colors, with clear text labels and axes. Set viewBox appropriately.
- A styled `<table>` listing the Top 3-5 Performing Posts across the quarter (Date, Platform, Topic, Reach/Engagement).

<h2>3. Events & Activities</h2>
- A `<table>` listing the 5 most significant events (Date, Event Name, Attendance/Impact).
- Provide a brief `<p>` analyzing the overall success and engagement of these events.

<h2>4. Media & Press Coverage</h2>
- Metric cards for Number of Press Releases and Total Media Mentions.
- A bulleted list `<ul>` of key newspapers, channels, or online portals that covered the university.

<h2>5. Key Takeaways & Recommendations</h2>
<ul>
<li>3–5 actionable bullet points on what worked and what to improve next quarter based on the data.</li>
</ul>

IMPORTANT RULES: 
- Output ONLY valid HTML. Do not wrap in markdown codeblocks (like ```html). 
- Do NOT use markdown formatting like **bold**. You MUST use HTML <strong> tags for emphasis.
- Create professional, accurate SVG charts based on the real data in the documents. 
- Use the exact CSS classes provided. Do not use inline styles unless necessary for the SVG drawing.
- Extract actual numbers and names from the PDF reports. Ensure accurate consolidation across {len(saved_paths)} months.
"""
        # Send the consolidated text prompt to Gemini
        print(f"[upload_document_report] Generating final HTML report from consolidated data...")
        
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
        )

        raw = response.text or ''
        
        # Fallback: if Gemini returns markdown bold despite instructions, convert it
        import re
        raw = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', raw)
        
        # Fallback: if Gemini returns markdown despite instructions, convert it
        if '<h2>' not in raw and '<p>' not in raw:
            import markdown
            raw = markdown.markdown(raw, extensions=['extra'])
        ai_summary = raw

    except Exception as exc:
        err_str = str(exc)
        print(f"[upload_document_report] Gemini Generation Error: {err_str}")
        
        err_msg = (
            "An error occurred while generating the AI summary. "
            f"Details: {err_str}"
        )

        ai_summary = (
            f"<div style='padding:16px 20px;background:#fef2f2;"
            f"border:1px solid #fecaca;border-radius:8px;"
            f"font-size:14px;color:#b91c1c;margin:20px 0;'>"
            f"<h3 style='margin-top:0;margin-bottom:8px;font-size:16px;color:#991b1b;'><i class='ph ph-warning-circle'></i> AI Generation Failed</h3>"
            f"{err_msg}</div>"
        )
    finally:
        pass

    # ── Generate output PDF ───────────────────────────────────────────────────
    context = {
        'title': title,
        'quarter': quarter,
        'quarter_label': quarter_label,
        'year': year,
        'ai_summary': ai_summary,
        'uploaded_by': request.user.get_full_name() or request.user.username,
        'months_covered': months_uploaded if 'months_uploaded' in dir() else quarter_label,
    }
    html_string = render_to_string('reports/doc_quarterly_template.html', context)

    import pathlib
    out_dir = settings.MEDIA_ROOT / 'reports' / 'doc_quarterly'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_filename = f"DocQ{quarter}_{year}_u{request.user.id}.pdf"
    out_path     = out_dir / out_filename

    try:
        from weasyprint import HTML as WeasyprintHTML
        WeasyprintHTML(string=html_string).write_pdf(out_path)
        pdf_relative = f'reports/doc_quarterly/{out_filename}'
    except Exception:
        pdf_relative = None

    # ── Save to DB ────────────────────────────────────────────────────────────
    report = UploadedDocumentReport.objects.create(
        title=title,
        quarter=quarter,
        year=year,
        source_file_1=saved_relative[0] if len(saved_relative) > 0 else '',
        source_file_2=saved_relative[1] if len(saved_relative) > 1 else None,
        source_file_3=saved_relative[2] if len(saved_relative) > 2 else None,
        ai_summary=ai_summary,
        output_pdf=pdf_relative,
        uploaded_by=request.user,
    )
    return redirect('preview_document_report', report_id=report.id)


@login_required
def preview_document_report(request, report_id):
    report = get_object_or_404(UploadedDocumentReport, id=report_id)
    return render(request, 'reports/preview_document_report.html', {'report': report})

