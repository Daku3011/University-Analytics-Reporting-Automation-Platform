import pathlib
import uuid
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse
from django.utils.text import get_valid_filename
from celery.result import AsyncResult

from reports.models import UploadedDocumentReport

ALLOWED_EXTENSIONS = {'pdf'}

def _save_uploaded_file(ufile, prefix):
    """Stream-save an uploaded file to disk without loading it all into memory."""
    upload_dir = settings.MEDIA_ROOT / 'reports' / 'uploaded_sources'
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    orig_path = pathlib.Path(ufile.name)
    ext = orig_path.suffix.lower()
    if ext != '.pdf':
        raise ValueError("Only PDF files allowed")
        
    clean_stem = get_valid_filename(orig_path.stem)
    safe_name = f"{prefix}_{clean_stem}_{uuid.uuid4().hex}{ext}"
    save_path = upload_dir / safe_name
    
    with open(save_path, 'wb') as fout:
        for chunk in ufile.chunks(chunk_size=8 * 1024 * 1024):   # 8 MB chunks
            fout.write(chunk)
    return save_path, f'reports/uploaded_sources/{safe_name}'


@login_required
def upload_document_report(request):
    """
    Faculty uploads up to 3 monthly PDF reports (Jan + Feb + Mar, each up to 70 MB).
    Each PDF is saved to disk, uploaded to Gemini Files API, then Gemini reads all
    three and condenses them into a professional 3-month quarterly summary PDF.
    """
    if request.method != 'POST':
        return redirect('report_dashboard')

    title = request.POST.get('doc_title', '').strip() or 'Uploaded Report'
    quarter_str = request.POST.get('doc_quarter')
    year_str = request.POST.get('doc_year')
    try:
        quarter = int(quarter_str) if quarter_str else 1
        year = int(year_str) if year_str else date.today().year
    except ValueError:
        messages.error(request, "Quarter and Year must be valid numeric values.")
        return redirect('report_dashboard')

    if quarter not in [1, 2, 3, 4]:
        messages.error(request, "Quarter must be between 1 and 4.")
        return redirect('report_dashboard')

    # Collect the uploaded files
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
        return redirect('report_dashboard')

    # Validate extensions
    for f in files_in:
        ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else ''
        if ext not in ALLOWED_EXTENSIONS:
            messages.error(request,
                f"File '{f.name}' is not a PDF. Only PDF files are supported. "
                f"Got extension: '{ext}' — allowed: {ALLOWED_EXTENSIONS}")
            return redirect('report_dashboard')

    # Save each file to disk
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

    # Dispatch Celery Task
    from reports.tasks import process_uploaded_document_report
    
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
