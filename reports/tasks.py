import os
import re
from pathlib import Path

import markdown
from celery import shared_task
from django.conf import settings
from django.template.loader import render_to_string

from .models import SeminarEventReport, UploadedDocumentReport


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

        def split_pdf_if_needed(fpath, max_size_mb=20):
            file_size_mb = os.path.getsize(fpath) / (1024 * 1024)
            if file_size_mb <= max_size_mb:
                return [fpath]

            try:
                from pypdf import PdfReader, PdfWriter
            except ImportError:
                print('[upload_document_report] pypdf not installed, cannot split.')
                return [fpath]

            reader = PdfReader(fpath)
            total_pages = len(reader.pages)
            num_chunks = int((file_size_mb // max_size_mb) + 1)
            pages_per_chunk = (total_pages // num_chunks) + 1

            chunk_paths = []
            for j in range(num_chunks):
                start_page = j * pages_per_chunk
                end_page = min((j + 1) * pages_per_chunk, total_pages)
                if start_page >= total_pages:
                    break

                writer = PdfWriter()
                for page_num in range(start_page, end_page):
                    writer.add_page(reader.pages[page_num])

                chunk_path = Path(fpath).parent / f"{Path(fpath).stem}_chunk{j + 1}.pdf"
                with open(chunk_path, 'wb') as f_out:
                    writer.write(f_out)
                chunk_paths.append(str(chunk_path))

            return chunk_paths

        for i, fpath_str in enumerate(saved_paths):
            fpath = Path(fpath_str)
            self.update_state(state='PROGRESS', meta={'message': f'Processing {fpath.name}...'})
            chunk_paths = split_pdf_if_needed(fpath_str)

            uploaded_gfiles = []
            for chunk_path in chunk_paths:
                uploaded_gfiles.append(client.files.upload(file=chunk_path))

            month_name = quarter_months[i] if i < len(quarter_months) else f'Month {i + 1}'
            map_prompt = f"Extract core metrics and activities for {month_name} {year}. Return strict JSON with month, executive_summary, social_metrics, top_posts, events, media_coverage, press_releases, takeaways."

            try:
                from google.genai import types as genai_types

                self.update_state(state='PROGRESS', meta={'message': f'Extracting data for {fpath.name}...'})
                resp = client.models.generate_content(
                    model=model_name,
                    contents=uploaded_gfiles + [map_prompt],
                    config=genai_types.GenerateContentConfig(http_options={'timeout': 300000}),
                )
                extracted_data_list.append(resp.text)
            except Exception as exc:
                print(f'[upload_document_report] Could not extract data from {fpath.name}: {exc}')
                extracted_data_list.append(
                    f'''{{
                    "month": "{month_name}",
                    "executive_summary": "Data could not be automatically extracted for this month.",
                    "social_metrics": {{"total_reach": 0, "total_views": 0, "followers_gained": 0}},
                    "top_posts": [],
                    "events": [],
                    "media_coverage": {{"total_placements": 0, "total_reach": 0, "key_mentions": []}},
                    "press_releases": 0,
                    "takeaways": ["Please review this month manually."]
                }}'''
                )
            finally:
                for uf in uploaded_gfiles:
                    try:
                        client.files.delete(name=uf.name)
                    except Exception as cleanup_exc:
                        print(f'[upload_document_report] Cleanup warning for {uf.name}: {cleanup_exc}')

        months_uploaded = ', '.join(quarter_months[: len(saved_paths)])
        combined_json_text = '\n\n'.join([f'--- Data Extract {i + 1} ---\n{data}' for i, data in enumerate(extracted_data_list)])

        self.update_state(state='PROGRESS', meta={'message': 'Generating final report with honest analysis...'})
        prompt = f"""You are a brutally honest data analyst for Sarvajanik University.
The following JSON data represents the extracted metrics and activities for the months of {months_uploaded} {year}.

RAW EXTRACTED DATA:
{combined_json_text}

Produce a professional {quarter_label} Quarterly Summary Report in clean HTML.
Use metric cards, SVG charts, tables, and highlight quotes. Output ONLY valid HTML.
"""

        from google.genai import types as genai_types

        response = client.models.generate_content(
            model=model_name,
            contents=prompt,
            config=genai_types.GenerateContentConfig(http_options={'timeout': 300000}),
        )
        raw = response.text or ''
        raw = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', raw)
        if '<h2>' not in raw and '<p>' not in raw:
            raw = markdown.markdown(raw, extensions=['extra'])
        ai_summary = raw
    except Exception as exc:
        err_str = str(exc)
        ai_summary = (
            f"<div style='padding:16px 20px;background:#fef2f2;border:1px solid #fecaca;border-radius:8px;font-size:14px;color:#b91c1c;margin:20px 0;'>"
            f"<h3 style='margin-top:0;margin-bottom:8px;font-size:16px;color:#991b1b;'>AI Generation Failed</h3>"
            f"<p>{err_str}</p></div>"
        )

    self.update_state(state='PROGRESS', meta={'message': 'Compiling PDF...'})

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
    out_filename = f'DocQ{quarter}_{year}_u{uploaded_by_id}.pdf'
    out_path = out_dir / out_filename

    try:
        from reports.services.pdf_service import PDFService

        PDFService.compile_html_to_pdf(html_string, out_path)
        pdf_relative = f'reports/doc_quarterly/{out_filename}'
    except Exception as exc:
        print(f'WeasyPrint failed: {exc}')
        pdf_relative = None

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
        uploaded_by_id=uploaded_by_id,
    )

    return {'report_id': report.id, 'redirect_url': f'/reports/preview-document/{report.id}/'}


@shared_task(bind=True)
def process_seminar_event_report(self, report_id, audio_file_path=None, document_paths=None, photo_paths=None):
    from django.conf import settings
    from google import genai
    from google.genai import types as genai_types
    from django.template.loader import render_to_string
    from pathlib import Path
    import os
    import time

    report = SeminarEventReport.objects.get(id=report_id)
    report.status = 'processing'
    report.save()

    self.update_state(state='PROGRESS', meta={'message': 'Initializing Gemini Client...'})

    api_key = os.environ.get('GEMINI_API_KEY', '')
    gemini_config = getattr(settings, 'GEMINI_CONFIG', {})
    model_name = gemini_config.get('MODEL', 'gemini-2.5-flash')
    client = genai.Client(api_key=api_key)
    uploaded_gfiles = []

    try:
        def upload_file_to_gemini(fpath_str, mime_type=None):
            fpath = Path(fpath_str)
            if not fpath.exists():
                print(f'[process_seminar_event_report] File not found: {fpath_str}')
                return None

            if mime_type:
                gfile = client.files.upload(
                    file=str(fpath),
                    config=genai_types.UploadFileConfig(mime_type=mime_type, display_name=fpath.name),
                )
            else:
                gfile = client.files.upload(file=str(fpath))

            waited = 0
            while gfile.state.name == 'PROCESSING' and waited < 300:
                time.sleep(2)
                waited += 2
                gfile = client.files.get(name=gfile.name)

            if gfile.state.name != 'ACTIVE':
                raise Exception(f'Gemini file state failed: {gfile.state.name}')

            uploaded_gfiles.append(gfile)
            return gfile

        g_audio = None
        if audio_file_path:
            self.update_state(state='PROGRESS', meta={'message': 'Uploading audio recording...'})
            ext = Path(audio_file_path).suffix.lower()
            mime = 'audio/webm'
            if ext == '.wav':
                mime = 'audio/wav'
            elif ext == '.mp3':
                mime = 'audio/mp3'
            elif ext == '.m4a':
                mime = 'audio/m4a'
            g_audio = upload_file_to_gemini(audio_file_path, mime_type=mime)

        g_docs = []
        if document_paths:
            for i, doc_path in enumerate(document_paths):
                self.update_state(state='PROGRESS', meta={'message': f'Uploading supporting document {i + 1}...'})
                g_doc = upload_file_to_gemini(doc_path, mime_type='application/pdf')
                if g_doc:
                    g_docs.append(g_doc)

        g_photos = []
        if photo_paths:
            for i, photo_path in enumerate(photo_paths):
                self.update_state(state='PROGRESS', meta={'message': f'Uploading photograph {i + 1}...'})
                ext = Path(photo_path).suffix.lower()
                mime = 'image/jpeg'
                if ext == '.png':
                    mime = 'image/png'
                elif ext == '.webp':
                    mime = 'image/webp'
                g_photo = upload_file_to_gemini(photo_path, mime_type=mime)
                if g_photo:
                    g_photos.append(g_photo)

        self.update_state(state='PROGRESS', meta={'message': 'Synthesizing report with Gemini Multimodal AI...'})

        prompt = f"""You are an elite, brutally honest educational event analyst for Sarvajanik University.
Analyze the seminar based on the provided audio, transcript, documents, and photographs.

Event title: {report.title}
College/Institute: {report.college.name}
Date: {report.date}
Faculty Speaker: {report.speaker_name or 'Not Specified'}
Social Media Mentions & Drafts: {report.social_media_posts or 'None Provided'}
Extra Transcript/Speaker Notes: {report.transcript_text or 'None Provided'}

Return only valid HTML using sections for executive summary, transcript messages, photographic analysis, supporting materials, outreach suggestions, and strategic action items.
"""

        contents = []
        if g_audio:
            contents.append(g_audio)
        contents.extend(g_docs)
        contents.extend(g_photos)
        contents.append(prompt)

        response = client.models.generate_content(
            model=model_name,
            contents=contents,
            config=genai_types.GenerateContentConfig(http_options={'timeout': 300000}),
        )
        ai_summary = response.text or ''
        ai_summary = re.sub(r'^```html\s*', '', ai_summary.strip(), flags=re.IGNORECASE)
        ai_summary = re.sub(r'\s*```$', '', ai_summary.strip())
        ai_summary = re.sub(r'^```\s*', '', ai_summary.strip())
        ai_summary = re.sub(r'\*\*(.*?)\*\*', r'<strong>\1</strong>', ai_summary)
        if '<h2>' not in ai_summary and '<p>' not in ai_summary:
            ai_summary = markdown.markdown(ai_summary, extensions=['extra'])
    except Exception as exc:
        err_str = str(exc)
        print(f'[process_seminar_event_report] Gemini error: {err_str}')
        ai_summary = f"<div class='alert alert-danger'><h4>Gemini Generation Failed</h4><p>{err_str}</p></div>"
    finally:
        for uf in uploaded_gfiles:
            try:
                client.files.delete(name=uf.name)
            except Exception as cleanup_exc:
                print(f'[process_seminar_event_report] Cleanup error for {uf.name}: {cleanup_exc}')

    self.update_state(state='PROGRESS', meta={'message': 'Compiling PDF Report...'})

    try:
        uploaded_by_name = 'System'
        if report.uploaded_by:
            uploaded_by_name = report.uploaded_by.get_full_name() or report.uploaded_by.username
    except Exception:
        uploaded_by_name = 'System'

    local_photo_paths = []
    for ph_field in [report.photo_1, report.photo_2, report.photo_3, report.photo_4, report.photo_5]:
        if ph_field:
            try:
                abs_path = ph_field.path
                if abs_path and Path(abs_path).exists():
                    local_photo_paths.append(abs_path)
            except Exception as ph_err:
                print(f'[process_seminar_event_report] Photo path error: {ph_err}')

    context = {
        'report': report,
        'ai_summary': ai_summary,
        'uploaded_by': uploaded_by_name,
        'photo_paths': local_photo_paths,
    }

    html_string = render_to_string('reports/seminar_report_template.html', context)

    out_dir = settings.MEDIA_ROOT / 'reports' / 'seminars' / 'pdf'
    out_dir.mkdir(parents=True, exist_ok=True)
    out_filename = f'Seminar_{report.id}_{int(time.time())}.pdf'
    out_path = out_dir / out_filename

    try:
        from reports.services.pdf_service import PDFService

        PDFService.compile_html_to_pdf(html_string, out_path)
        pdf_relative = f'reports/seminars/pdf/{out_filename}'
    except Exception as exc:
        print(f'[process_seminar_event_report] WeasyPrint failed: {exc}')
        pdf_relative = None

    report.ai_summary = ai_summary
    report.output_pdf = pdf_relative
    report.status = 'success' if pdf_relative else 'failed'
    if not pdf_relative:
        report.error_message = 'PDF generation failed via WeasyPrint.'
    report.save()

    return {'report_id': report.id, 'redirect_url': f'/reports/seminar/preview/{report.id}/'}
