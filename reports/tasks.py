import os
import json
import re
from pathlib import Path
from datetime import date
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string
from .models import UploadedDocumentReport
import markdown

ALLOWED_EXTENSIONS = {'pdf'}

@shared_task(bind=True)
def process_uploaded_document_report(self, title, quarter, year, uploaded_by_id, saved_paths, saved_relative, quarter_label, quarter_months):
    ai_summary = ''
    gemini_config = getattr(settings, 'GEMINI_CONFIG', {})
    model_name = gemini_config.get('MODEL', 'gemini-2.5-flash')
    api_key = os.environ.get('GEMINI_API_KEY', '')
    
    extracted_data_list = []
    
    try:
        from google import genai
        client = genai.Client(api_key=api_key)
        
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
                
            print(f"[upload_document_report] Splitting {Path(fpath).name} ({file_size_mb:.1f}MB) into chunks...")
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
                    
                chunk_path = Path(fpath).parent / f"{Path(fpath).stem}_chunk{j+1}.pdf"
                with open(chunk_path, "wb") as f_out:
                    writer.write(f_out)
                chunk_paths.append(str(chunk_path))
            return chunk_paths

        # ── Map Phase: Extract JSON data from each file individually ──
        for i, fpath_str in enumerate(saved_paths):
            fpath = Path(fpath_str)
            self.update_state(state='PROGRESS', meta={'message': f'Processing {fpath.name}...'})
            print(f"[upload_document_report] Processing {fpath.name}...")
            chunk_paths = split_pdf_if_needed(fpath_str)
            
            uploaded_gfiles = []
            for chunk_path in chunk_paths:
                print(f"[upload_document_report] Uploading {Path(chunk_path).name} to Gemini...")
                gfile = client.files.upload(file=chunk_path)
                uploaded_gfiles.append(gfile)
            
            try:
                self.update_state(state='PROGRESS', meta={'message': f'Extracting data for {fpath.name}...'})
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
                    from google.genai import types as genai_types
                    resp = client.models.generate_content(
                        model=model_name,
                        contents=uploaded_gfiles + [map_prompt],
                        config=genai_types.GenerateContentConfig(
                            http_options={'timeout': 300000}
                        )
                    )
                except Exception as map_exc:
                    if 'INVALID_ARGUMENT' in str(map_exc) or '400' in str(map_exc):
                        print(f"[upload_document_report] {model_name} failed with INVALID_ARGUMENT for {fpath.name}. Retrying with gemini-2.5-pro...")
                        try:
                            from google.genai import types as genai_types
                            resp = client.models.generate_content(
                                model="gemini-2.5-pro",
                                contents=uploaded_gfiles + [map_prompt],
                                config=genai_types.GenerateContentConfig(
                                    http_options={'timeout': 300000}
                                )
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

        self.update_state(state='PROGRESS', meta={'message': 'Generating final report with honest analysis...'})
        # ── Reduce Phase: Generate final HTML report from the consolidated JSON ──
        prompt = f"""You are a brutally honest data analyst for Sarvajanik University. Your job is to tell the truth — no sugar coating, no corporate fluff.

The following JSON data represents the extracted metrics and activities for the months of {months_uploaded} {year}.

RAW EXTRACTED DATA:
{combined_json_text}

Your task: Produce a highly visual, professional **{quarter_label} Quarterly Summary Report** in clean HTML.
Use data visualization (SVG), metric cards, and data tables to summarize the data.

You must exclusively output HTML using these specific CSS classes which are already defined:
- `<div class="metric-grid">` containing `<div class="metric-card"><div class="metric-value">X</div><div class="metric-label">Y</div></div>`
- `<div class="chart-container">` containing raw, well-formatted `<svg>` code for charts.
- Standard `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` for tabular data.
- `<div class="highlight-quote">` for important text highlights, quotes, or overarching quarter themes.

Structure your response exactly into these sections:

<h2>1. Quarter Overview</h2>
- Start with a `<div class="highlight-quote">` with a punchy, honest one-liner summarizing the quarter's reality.
- Follow with a `<div class="metric-grid">` showing 3-4 top-level aggregate metrics for the quarter (e.g., Total Reach, Total Events, New Followers, Total PR).

<h2>2. Month-by-Month Comparison — Who Won and Who Lost</h2>
- Compare each month head-to-head on: total views, reach, followers gained, events held.
- Use an inline SVG bar chart comparing key metrics across the months. Use #4f46e5 and #7c3aed colors.
- A `<table>` with monthly breakdown.
- <strong>Call out specifically which month performed best and which performed worst.</strong> Say exactly why — be direct. If a month declined, say it.

<h2>3. Social Media Performance — What Worked and What Didn't</h2>
- Use metric cards for platform-specific stats (Instagram, Facebook, YouTube).
- SVG chart comparing reach/views across platforms.
- A styled `<table>` listing the Top 3-5 Performing Posts across the quarter.
- Add a <strong>blunt paragraph</strong>: which platform underperformed, what content type flopped, what engagement tells us.

<h2>4. Events & Activities</h2>
- A `<table>` listing the 5 most significant events (Date, Event Name, Attendance/Impact).
- Analysis paragraph: were events well-attended? Were there enough events? Which categories dominated?

<h2>5. Media & Press Coverage</h2>
- Metric cards for Number of Press Releases and Total Media Mentions.
- Bulleted list `<ul>` of key newspapers, channels, or online portals.

<h2>6. Honest Recommendations — What Must Change</h2>
<ul>
<li>5–7 brutally honest, actionable recommendations. No generic advice. Specific: "Instagram Reels dropped 40% in March — need minimum 8 reels per month", "Events in February had highest engagement — replicate the Carnival format in Q2", etc.</li>
<li>Call out specific weaknesses by name.</li>
</ul>

IMPORTANT RULES: 
- Output ONLY valid HTML. Do not wrap in markdown codeblocks (like ```html). 
- Do NOT use markdown formatting like **bold**. You MUST use HTML <strong> tags for emphasis.
- Create professional, accurate SVG charts based on the real data in the documents. 
- Use the exact CSS classes provided. Do not use inline styles unless necessary for the SVG drawing.
- Extract actual numbers and names from the PDF reports. Ensure accurate consolidation across {len(saved_paths)} months.
- BE HONEST. If something declined, say it declined. If something failed, say it failed. If something improved, acknowledge it.
"""
        # Send the consolidated text prompt to Gemini
        print(f"[upload_document_report] Generating final HTML report from consolidated data...")
        
        from google.genai import types as genai_types
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                http_options={'timeout': 300000}
            )
        )

        raw = response.text or ''
        
        # Fallback: if Gemini returns markdown bold despite instructions, convert it
        raw = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', raw)
        
        # Fallback: if Gemini returns markdown despite instructions, convert it
        if '<h2>' not in raw and '<p>' not in raw:
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

    self.update_state(state='PROGRESS', meta={'message': 'Compiling PDF...'})
    # ── Generate output PDF ───────────────────────────────────────────────────
    # We must fetch user name since we only have user id
    from django.contrib.auth.models import User
    try:
        user = User.objects.get(id=uploaded_by_id)
        uploaded_by_name = user.get_full_name() or user.username
    except Exception:
        uploaded_by_name = 'System'

    context = {
        'title': title,
        'quarter': quarter,
        'quarter_label': quarter_label,
        'year': year,
        'ai_summary': ai_summary,
        'uploaded_by': uploaded_by_name,
        'months_covered': months_uploaded if 'months_uploaded' in locals() else quarter_label,
    }
    html_string = render_to_string('reports/doc_quarterly_template.html', context)

    out_dir = settings.MEDIA_ROOT / 'reports' / 'doc_quarterly'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_filename = f"DocQ{quarter}_{year}_u{uploaded_by_id}.pdf"
    out_path     = out_dir / out_filename

    try:
        from reports.services.pdf_service import PDFService
        PDFService.compile_html_to_pdf(html_string, out_path)
        pdf_relative = f'reports/doc_quarterly/{out_filename}'
    except Exception as e:
        print(f"WeasyPrint failed: {e}")
        pdf_relative = None

    # ── Save to DB ────────────────────────────────────────────────────────────
    self.update_state(state='PROGRESS', meta={'message': 'Saving report...'})
    report = UploadedDocumentReport.objects.create(
        title=title,
        quarter=quarter,
        year=year,
        source_file_1=saved_relative[0] if len(saved_relative) > 0 else '',
        source_file_2=saved_relative[1] if len(saved_relative) > 1 else None,
        source_file_3=saved_relative[2] if len(saved_relative) > 2 else None,
        ai_summary=ai_summary,
        output_pdf=pdf_relative,
        uploaded_by_id=uploaded_by_id
    )
    
    return {'report_id': report.id, 'redirect_url': f"/reports/preview-document/{report.id}/"}


@shared_task(bind=True)
def process_batch_file_task(self, file_id):
    """
    Map Phase: Ingests a single uploaded PDF file, uploads it to Gemini via the Files API,
    extracts structured category-specific metrics and takeaways as a JSON object,
    stores it in the BatchUploadFile record, and deletes the file from Gemini storage.
    """
    from reports.models import BatchUploadFile
    from google import genai
    from google.genai import types as genai_types
    from django.conf import settings
    from reports.services.gemini_service import GeminiService
    from pathlib import Path
    import os
    import json
    
    try:
        batch_file = BatchUploadFile.objects.get(id=file_id)
    except BatchUploadFile.DoesNotExist:
        print(f"[process_batch_file_task] Batch file with ID {file_id} not found.")
        return
        
    batch_file.status = 'processing'
    batch_file.save()
    
    file_path = Path(batch_file.file.path)
    category = batch_file.category
    filename = batch_file.filename
    
    gemini_config = getattr(settings, 'GEMINI_CONFIG', {})
    model_name = gemini_config.get('MODEL', 'gemini-2.5-flash')
    api_key = os.environ.get('GEMINI_API_KEY', '')
    
    uploaded_gfile = None
    
    try:
        # 1. Upload file using GeminiService.upload_and_wait (polls until ACTIVE)
        print(f"[process_batch_file_task] Uploading {filename} ({category}) to Gemini Files API...")
        uploaded_gfile = GeminiService.upload_and_wait(file_path)
        print(f"[process_batch_file_task] Uploaded and ACTIVE. File name: {uploaded_gfile.name}")
        
        client = GeminiService.get_client()
        
        # 2. Formulate prompt based on category
        if category == 'social_media':
            prompt = """Analyze the provided social media report. Extract core metrics and monthly highlights.
Please output a strict JSON object with this exact structure:
{
  "category": "social_media",
  "filename": "%s",
  "month": "Month Name and Year (e.g. June 2025)",
  "total_reach": 12345, // numeric
  "total_views": 67890, // numeric
  "followers_gained": 345, // numeric
  "top_posts": [
    {"date": "Date", "platform": "Instagram/FB/YT", "topic": "Brief Topic", "reach": 1200}
  ],
  "takeaways": [
    "takeaway bullet point 1",
    "takeaway bullet point 2"
  ]
}
Return ONLY valid JSON. Do not wrap in ```json.""" % filename

        elif category == 'digital_print':
            prompt = """Analyze the provided digital print media report. Extract media placements, key articles and tone.
Please output a strict JSON object with this exact structure:
{
  "category": "digital_print",
  "filename": "%s",
  "month": "Month Name and Year (e.g. June 2025)",
  "total_placements": 15, // numeric
  "estimated_reach": 50000, // numeric
  "key_outlets": ["Outlet 1", "Outlet 2"],
  "top_stories": [
    {"title": "Article Title", "outlet": "News Portal", "date": "Date", "sentiment": "Positive/Neutral/Negative"}
  ],
  "takeaways": [
    "takeaway bullet point 1",
    "takeaway bullet point 2"
  ]
}
Return ONLY valid JSON. Do not wrap in ```json.""" % filename

        else: # physical_newspaper
            prompt = """Analyze the provided physical newspaper report/clippings. Extract publication records, headlines, and page placement.
Please output a strict JSON object with this exact structure:
{
  "category": "physical_newspaper",
  "filename": "%s",
  "month": "Month Name and Year (e.g. June 2025)",
  "total_clippings": 8, // numeric
  "publications": ["Times of India", "Gujarat Samachar"],
  "top_headlines": [
    {"headline": "Headline text", "publication": "Paper Name", "date": "Date", "page": "Page number/details"}
  ],
  "takeaways": [
    "takeaway bullet point 1",
    "takeaway bullet point 2"
  ]
}
Return ONLY valid JSON. Do not wrap in ```json.""" % filename
        
        # 3. Generate content from Gemini
        response = client.models.generate_content(
            model=model_name,
            contents=[uploaded_gfile, prompt],
            config=genai_types.GenerateContentConfig(
                http_options={'timeout': 300000}
            )
        )
        
        response_text = response.text or ''
        response_text = response_text.strip()
        if response_text.startswith("```"):
            lines = response_text.splitlines()
            if lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            response_text = "\n".join(lines).strip()
            
        # Verify JSON validity
        try:
            parsed_json = json.loads(response_text)
            batch_file.extracted_json = json.dumps(parsed_json)
            batch_file.status = 'success'
            batch_file.error_message = ''
            print(f"[process_batch_file_task] Successfully processed {filename}.")
        except Exception as json_exc:
            batch_file.status = 'failed'
            batch_file.error_message = f"Failed to parse JSON output: {json_exc}. Raw output: {response_text[:300]}"
            print(f"[process_batch_file_task] JSON parsing failed for {filename}.")
            
    except Exception as exc:
        from celery.exceptions import Retry
        if isinstance(exc, Retry):
            raise exc
            
        print(f"[process_batch_file_task] Task failed for {filename}: {exc}")
        
        retries = self.request.retries
        if retries < 5:
            batch_file.status = 'pending'
            batch_file.error_message = f"Transient error: {exc}. Retrying... (Attempt {retries + 1}/5)"
            raise self.retry(exc=exc, countdown=45, max_retries=5)
        else:
            batch_file.status = 'failed'
            batch_file.error_message = str(exc)
        
    finally:
        # 4. Clean up Files API
        if uploaded_gfile:
            try:
                GeminiService.delete_file(uploaded_gfile.name)
                print(f"[process_batch_file_task] Deleted {uploaded_gfile.name} from Gemini Files API.")
            except Exception as cleanup_exc:
                print(f"[process_batch_file_task] Cleanup warning for {uploaded_gfile.name}: {cleanup_exc}")
        batch_file.save()


@shared_task(bind=True)
def generate_annual_report_task(self, title, start_date_str, end_date_str, uploaded_by_id, file_ids, category='all'):
    """
    Reduce Phase: Gathers all extracted monthly JSON data blocks, consolidates them,
    sends a detailed synthesis prompt to Gemini to write the HTML annual report,
    and runs WeasyPrint to compile the final annual summary PDF.
    """
    from reports.models import BatchUploadFile, AnnualCategoryReport
    from google import genai
    from google.genai import types as genai_types
    from django.conf import settings
    from django.contrib.auth.models import User
    from reports.services.gemini_service import GeminiService
    import os
    import json
    import re
    import markdown
    from datetime import datetime
    
    self.update_state(state='PROGRESS', meta={'message': 'Aggregating extracted data...'})
    
    # 1. Fetch successful files
    files = BatchUploadFile.objects.filter(id__in=file_ids, status='success')
    
    social_data = []
    digital_data = []
    physical_data = []
    
    for f in files:
        try:
            data = json.loads(f.extracted_json)
            if f.category == 'social_media':
                social_data.append(data)
            elif f.category == 'digital_print':
                digital_data.append(data)
            elif f.category == 'physical_newspaper':
                physical_data.append(data)
        except Exception as e:
            print(f"[generate_annual_report_task] Error parsing JSON for file {f.id}: {e}")
            
    # Sort data chronologically by month
    def try_sort_by_month(data_list):
        month_order = {
            'january': 1, 'february': 2, 'march': 3, 'april': 4, 'may': 5, 'june': 6,
            'july': 7, 'august': 8, 'september': 9, 'october': 10, 'november': 11, 'december': 12
        }
        def get_key(item):
            month_str = item.get('month', '').lower()
            year_val = 0
            month_val = 0
            
            year_match = re.search(r'\b(20\d{2})\b', month_str)
            if year_match:
                year_val = int(year_match.group(1))
            
            for m_name, m_val in month_order.items():
                if m_name in month_str:
                    month_val = m_val
                    break
            return (year_val, month_val)
        try:
            return sorted(data_list, key=get_key)
        except Exception:
            return data_list

    social_data = try_sort_by_month(social_data)
    digital_data = try_sort_by_month(digital_data)
    physical_data = try_sort_by_month(physical_data)
    
    # 2. Formulate Prompt based on chosen category
    if category == 'social_media':
        payload_str = json.dumps({'social_media': social_data}, indent=2)
        prompt = f"""You are a brutally honest data analyst for Sarvajanik University. Your job is to compile an **Annual Social Media Performance Report** covering the period from {start_date_str} to {end_date_str}.
        
Here is the aggregated month-by-month extraction JSON from the uploaded Social Media reports:

AGGREGATED DATA:
{payload_str}

Please generate a stunning, visually rich, and professional HTML summary report auditing our social media presence. Use these exact CSS classes (no markdown codeblocks like ```html, output raw HTML directly):
- `<div class="metric-grid">` containing `<div class="metric-card"><div class="metric-value">X</div><div class="metric-label">Y</div></div>`
- `<div class="chart-container">` containing raw, beautifully formatted `<svg>` code for trend charts (use colors #4f46e5 and #7c3aed).
- Standard `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` for listing posts.
- `<div class="highlight-quote">` for overarching strategic summaries or highlights.

Structure your response exactly into these sections:

<h2>1. Executive Summary & Timeline Overview</h2>
- Start with a `<div class="highlight-quote">` providing a punchy, direct and brutally honest annual takeaway.
- Follow with a `<div class="metric-grid">` showing total summary figures:
  * Total Social Media Reach
  * Total Social Media Views
  * Total Followers Gained
  * Average monthly reach / views

<h2>2. Monthly Reach & View Trends (June 2025 – July 2026)</h2>
- Present MoM trends. Include an inline SVG line chart showing reach or views over time.
- Detail when the spikes occurred and what drove them.

<h2>3. Platform & Channel Breakdown</h2>
- Analyze platform performance (Instagram vs YouTube vs Facebook).
- A direct paragraph about what content failed and which platform underperformed.

<h2>4. Top Performing Content</h2>
- Table of top 5/10 most viral posts with date, platform, reach, and topic.

<h2>5. Key Strategic Recommendations (No generic corporate fluff)</h2>
- 6-8 direct, concrete, actionable, and specific recommendations on what the university must change (e.g., "Stop wasting effort on X platform", "Increase focus on Y format", "Target Z publication for physical coverage").
"""
    elif category == 'digital_print':
        payload_str = json.dumps({'digital_print': digital_data}, indent=2)
        prompt = f"""You are a brutally honest data analyst for Sarvajanik University. Your job is to compile an **Annual Digital Prints Performance Report** covering the period from {start_date_str} to {end_date_str}.
        
Here is the aggregated month-by-month extraction JSON from the uploaded Digital Print reports:

AGGREGATED DATA:
{payload_str}

Please generate a stunning, visually rich, and professional HTML summary report auditing our online news placements. Use these exact CSS classes (no markdown codeblocks like ```html, output raw HTML directly):
- `<div class="metric-grid">` containing `<div class="metric-card"><div class="metric-value">X</div><div class="metric-label">Y</div></div>`
- `<div class="chart-container">` containing raw, beautifully formatted `<svg>` code for trend charts (use colors #4f46e5 and #7c3aed).
- Standard `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` for listing articles/sentiment.
- `<div class="highlight-quote">` for overarching strategic summaries or highlights.

Structure your response exactly into these sections:

<h2>1. Executive Summary & Timeline Overview</h2>
- Start with a `<div class="highlight-quote">` providing a punchy, direct and brutally honest annual takeaway.
- Follow with a `<div class="metric-grid">` showing total summary figures:
  * Total Digital Placements count
  * Total estimated digital reach
  * Count of unique digital outlets publishing SU news

<h2>2. Placement Trends & Outlet Coverage</h2>
- Present MoM trends. Include an inline SVG chart showing placement counts over time.
- Detail periods of high media interest.

<h2>3. Media Outlets & Portal Breakdown</h2>
- Table of key media portals (Websites) that published SU stories, showing the counts and sentiment.
- A critical analysis of the digital outreach and its true influence.

<h2>4. Top Stories & Sentiment Audit</h2>
- Table of top placements showing story title, outlet, date, and sentiment.

<h2>5. Key Strategic Recommendations (No generic corporate fluff)</h2>
- 6-8 direct, concrete, actionable, and specific recommendations on what the university must change (e.g., "Stop wasting effort on X platform", "Increase focus on Y format", "Target Z publication for physical coverage").
"""
    elif category == 'physical_newspaper':
        payload_str = json.dumps({'physical_newspaper': physical_data}, indent=2)
        prompt = f"""You are a brutally honest data analyst for Sarvajanik University. Your job is to compile an **Annual Physical Newspaper Coverage Report** covering the period from {start_date_str} to {end_date_str}.
        
Here is the aggregated month-by-month extraction JSON from the uploaded Physical Newspaper reports:

AGGREGATED DATA:
{payload_str}

Please generate a stunning, visually rich, and professional HTML summary report auditing our newspaper clippings. Use these exact CSS classes (no markdown codeblocks like ```html, output raw HTML directly):
- `<div class="metric-grid">` containing `<div class="metric-card"><div class="metric-value">X</div><div class="metric-label">Y</div></div>`
- `<div class="chart-container">` containing raw, beautifully formatted `<svg>` code for trend charts (use colors #4f46e5 and #7c3aed).
- Standard `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` for listing clippings/headlines.
- `<div class="highlight-quote">` for overarching strategic summaries or highlights.

Structure your response exactly into these sections:

<h2>1. Executive Summary & Timeline Overview</h2>
- Start with a `<div class="highlight-quote">` providing a punchy, direct and brutally honest annual takeaway.
- Follow with a `<div class="metric-grid">` showing total summary figures:
  * Total Newspaper Clippings count
  * Total unique publications featuring SU news
  * Count of front-page or high-prominence placements

<h2>2. Coverage Trends & Layout Placement Analysis</h2>
- Present MoM trends. Include an inline SVG chart showing clipping counts over time.
- Clipping counts and layout placement analysis (e.g., page 1 placement vs inner page).

<h2>3. Newspapers & Publications Breakdown</h2>
- Table of top newspapers by count and key stories covered.
- Critical evaluation of whether physical print is worth the effort compared to digital.

<h2>4. Top Clippings & Headlines</h2>
- Table of top clippings showing headline, publication, date, and page/placement info.

<h2>5. Key Strategic Recommendations (No generic corporate fluff)</h2>
- 6-8 direct, concrete, actionable, and specific recommendations on what the university must change (e.g., "Stop wasting effort on X platform", "Increase focus on Y format", "Target Z publication for physical coverage").
"""
    else:
        combined_payload = {
            'social_media': social_data,
            'digital_print': digital_data,
            'physical_newspaper': physical_data
        }
        payload_str = json.dumps(combined_payload, indent=2)
        prompt = f"""You are a brutally honest data analyst for Sarvajanik University. Your job is to compile a comprehensive **Annual Category Performance Report** covering the period from {start_date_str} to {end_date_str}.
        
Here is the aggregated month-by-month extraction JSON from the uploaded reports across the three categories (Social Media, Digital Prints, Physical Newspapers):

AGGREGATED DATA:
{payload_str}

Please generate a stunning, visually rich, and professional HTML summary report using these exact CSS classes (no markdown codeblocks like ```html, output raw HTML directly):
- `<div class="metric-grid">` containing `<div class="metric-card"><div class="metric-value">X</div><div class="metric-label">Y</div></div>`
- `<div class="chart-container">` containing raw, beautifully formatted `<svg>` code for trend charts (use colors #4f46e5 and #7c3aed).
- Standard `<table>`, `<thead>`, `<tbody>`, `<tr>`, `<th>`, `<td>` for listing posts/clippings/articles.
- `<div class="highlight-quote">` for overarching strategic summaries or highlights.

Structure your response exactly into these sections:

<h2>1. Executive Summary & Timeline Overview</h2>
- Start with a `<div class="highlight-quote">` providing a punchy, direct and brutally honest annual takeaway.
- Follow with a `<div class="metric-grid">` showing total summary figures:
  * Total Social Media Reach & Views
  * Total Digital Placement count
  * Total Physical Clipping count
  * Total estimated annual audience reach (cross-category)

<h2>2. Social Media Performance (June 2025 – July 2026)</h2>
- Present MoM trends. Include an inline SVG line chart showing reach or views over time.
- Detail platform highlights (Instagram, Facebook, YouTube).
- Table of top 5 most viral posts across the entire year.
- A direct paragraph about what content failed and which platform underperformed.

<h2>3. Digital Print Placements</h2>
- Metric cards for Digital Prints.
- Table of key media portals (Websites) that published SU stories, showing the counts and sentiment.
- A critical analysis of the digital outreach and its true influence.

<h2>4. Physical Newspaper Coverage</h2>
- Clipping counts and layout placement analysis (e.g., page 1 placement vs inner page).
- List/Table of top newspapers by count and key stories covered.
- Critical evaluation of whether physical print is worth the effort compared to digital.

<h2>5. Cross-Category Correlation & Audit</h2>
- Direct evaluation of how campaigns/events translated across categories (e.g., did an event with high social media views get newspaper coverage?).
- Identify best and worst months for SU public relations.

<h2>6. Key Strategic Recommendations (No generic corporate fluff)</h2>
- 6-8 direct, concrete, actionable, and specific recommendations on what the university must change (e.g., "Stop wasting effort on X platform", "Increase focus on Y format", "Target Z publication for physical coverage").
"""

    self.update_state(state='PROGRESS', meta={'message': 'Synthesizing report with Gemini...'})
    
    gemini_config = getattr(settings, 'GEMINI_CONFIG', {})
    model_name = gemini_config.get('MODEL', 'gemini-2.5-flash')
    
    ai_summary = ""
    
    try:
        client = GeminiService.get_client()
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(
                http_options={'timeout': 300000}
            )
        )
        raw = response.text or ''
        
        # Cleanup markup
        raw = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', raw)
        if '<h2>' not in raw and '<p>' not in raw:
            raw = markdown.markdown(raw, extensions=['extra'])
        ai_summary = raw
    except Exception as exc:
        print(f"[generate_annual_report_task] Gemini failed: {exc}")
        ai_summary = f"<div class='alert alert-danger'>AI synthesis failed: {exc}</div>"
        
    self.update_state(state='PROGRESS', meta={'message': 'Compiling PDF via WeasyPrint...'})
    
    # Compile PDF
    try:
        user = User.objects.get(id=uploaded_by_id)
        uploaded_by_name = user.get_full_name() or user.username
    except Exception:
        uploaded_by_name = 'System'
        
    context = {
        'title': title,
        'start_date': start_date_str,
        'end_date': end_date_str,
        'ai_summary': ai_summary,
        'uploaded_by': uploaded_by_name,
        'created_at': datetime.now(),
    }
    
    html_string = render_to_string('reports/annual_report_template.html', context)
    
    out_dir = settings.MEDIA_ROOT / 'reports' / 'annual_summaries'
    out_dir.mkdir(parents=True, exist_ok=True)
    
    clean_title = "".join([c if c.isalnum() else "_" for c in title])
    out_filename = f"Annual_{clean_title}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"
    out_path = out_dir / out_filename
    
    try:
        from reports.services.pdf_service import PDFService
        PDFService.compile_html_to_pdf(html_string, out_path)
        pdf_relative = f'reports/annual_summaries/{out_filename}'
    except Exception as e:
        print(f"[generate_annual_report_task] WeasyPrint failed: {e}")
        pdf_relative = None
        
    # Save model record
    start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
    end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()
    
    self.update_state(state='PROGRESS', meta={'message': 'Saving record to database...'})
    report = AnnualCategoryReport.objects.create(
        title=title,
        category=category,
        start_date=start_date,
        end_date=end_date,
        ai_summary=ai_summary,
        output_pdf=pdf_relative,
        uploaded_by_id=uploaded_by_id
    )
    
    return {'report_id': report.id, 'redirect_url': f"/reports/annual-analyzer/preview/{report.id}/"}

