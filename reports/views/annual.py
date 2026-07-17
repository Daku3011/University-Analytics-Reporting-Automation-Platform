import pathlib
import uuid
from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.conf import settings
from django.http import JsonResponse, Http404
from django.utils.text import get_valid_filename
from celery.result import AsyncResult

from reports.models import BatchUploadFile, AnnualCategoryReport

ALLOWED_EXTENSIONS = {'pdf'}

def _save_uploaded_batch_file(ufile, category):
    """Stream-save an uploaded batch file to disk."""
    upload_dir = settings.MEDIA_ROOT / 'reports' / 'batch_uploaded_sources'
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    orig_path = pathlib.Path(ufile.name)
    ext = orig_path.suffix.lower()
    if ext != '.pdf':
        raise ValueError("Only PDF files allowed")
        
    clean_stem = get_valid_filename(orig_path.stem)
    safe_name = f"{category}_{clean_stem}_{uuid.uuid4().hex}{ext}"
    save_path = upload_dir / safe_name
    
    with open(save_path, 'wb') as fout:
        for chunk in ufile.chunks(chunk_size=8 * 1024 * 1024):
            fout.write(chunk)
    return save_path, f'reports/batch_uploaded_sources/{safe_name}'


@login_required
def annual_analyzer_dashboard(request):
    """Shows the main Annual Analyzer Dashboard with batch uploads and previous summaries."""
    uploaded_files = BatchUploadFile.objects.all().order_by('-created_at')
    generated_reports = AnnualCategoryReport.objects.all().order_by('-created_at')
    
    context = {
        'uploaded_files': uploaded_files,
        'generated_reports': generated_reports,
        'default_start_date': '2025-06-01',
        'default_end_date': '2026-07-31',
    }
    return render(request, 'reports/annual_analyzer.html', context)


@login_required
def ajax_upload_batch_file(request):
    """Handles async AJAX upload of a single PDF for a given category."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
        
    ufile = request.FILES.get('file')
    category = request.POST.get('category')
    
    if not ufile or not category:
        return JsonResponse({'error': 'Missing file or category'}, status=400)
        
    if category not in ['social_media', 'digital_print', 'physical_newspaper']:
        return JsonResponse({'error': 'Invalid category'}, status=400)
        
    ext = ufile.name.rsplit('.', 1)[-1].lower() if '.' in ufile.name else ''
    if ext not in ALLOWED_EXTENSIONS:
        return JsonResponse({'error': 'Only PDF files are supported.'}, status=400)
        
    try:
        path, rel = _save_uploaded_batch_file(ufile, category)
        
        batch_file = BatchUploadFile.objects.create(
            category=category,
            file=rel,
            filename=ufile.name,
            status='pending'
        )
        
        # Trigger the Celery task
        from reports.tasks import process_batch_file_task
        process_batch_file_task.delay(batch_file.id)
        
        return JsonResponse({
            'id': batch_file.id,
            'filename': batch_file.filename,
            'status': batch_file.status,
            'category': batch_file.category
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def ajax_delete_batch_file(request, file_id):
    """Deletes a batch uploaded file from DB and local disk."""
    if request.method != 'POST':
        return JsonResponse({'error': 'Invalid request method'}, status=400)
        
    batch_file = get_object_or_404(BatchUploadFile, id=file_id)
    
    # Delete file from disk
    if batch_file.file:
        try:
            file_path = pathlib.Path(batch_file.file.path)
            if file_path.exists():
                file_path.unlink()
        except Exception as e:
            print(f"[ajax_delete_batch_file] Error deleting file: {e}")
            
    batch_file.delete()
    return JsonResponse({'success': True})


@login_required
def ajax_get_batch_files_status(request):
    """API endpoint to poll status updates of all BatchUploadFiles."""
    files = BatchUploadFile.objects.all().order_by('-created_at')
    data = []
    for f in files:
        data.append({
            'id': f.id,
            'filename': f.filename,
            'category': f.category,
            'category_display': f.get_category_display(),
            'status': f.status,
            'error_message': f.error_message,
            'created_at': f.created_at.strftime('%Y-%m-%d %H:%M:%S')
        })
    return JsonResponse({'files': data})


@login_required
def generate_annual_summary(request):
    """Triggers the consolidation (reduce) Celery task to summarize all successful batch files."""
    if request.method != 'POST':
        return redirect('annual_analyzer')
        
    title = request.POST.get('title', '').strip() or 'Annual Category Summary'
    start_date = request.POST.get('start_date', '2025-06-01')
    end_date = request.POST.get('end_date', '2026-07-31')
    category = request.POST.get('category', 'all').strip()
    
    # Get all successful BatchUploadFile IDs for the selected category scope
    if category == 'all':
        successful_files = BatchUploadFile.objects.filter(status='success')
    else:
        successful_files = BatchUploadFile.objects.filter(status='success', category=category)
        
    file_ids = list(successful_files.values_list('id', flat=True))
    
    if not file_ids:
        category_name = dict(AnnualCategoryReport.CATEGORY_CHOICES).get(category, category)
        messages.error(request, f"No successfully processed report files found for the category: {category_name}. Please upload and let the system process files first.")
        return redirect('annual_analyzer')
        
    # Dispatch Celery Task
    from reports.tasks import generate_annual_report_task
    task = generate_annual_report_task.delay(
        title=title,
        start_date_str=start_date,
        end_date_str=end_date,
        uploaded_by_id=request.user.id,
        file_ids=file_ids,
        category=category
    )
    
    return redirect('annual_report_processing', task_id=task.id)


@login_required
def annual_report_processing(request, task_id):
    """Renders a processing page while the annual summary is compiling."""
    return render(request, 'reports/annual_report_processing.html', {'task_id': task_id})


@login_required
def preview_annual_report(request, report_id):
    """Preview view of the completed Annual Report."""
    report = get_object_or_404(AnnualCategoryReport, id=report_id)
    return render(request, 'reports/preview_annual_report.html', {'report': report})
