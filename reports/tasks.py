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
        
        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
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
    except:
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
        from weasyprint import HTML as WeasyprintHTML
        WeasyprintHTML(string=html_string).write_pdf(out_path)
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
