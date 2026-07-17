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

from reports.models import SeminarEventReport
from colleges.models import College
from reports.tasks import process_seminar_event_report


def _save_seminar_file(ufile, folder_name, prefix, allowed_extensions=None):
    """Saves an uploaded file to MEDIA_ROOT/reports/seminars/folder_name/."""
    upload_dir = settings.MEDIA_ROOT / 'reports' / 'seminars' / folder_name
    upload_dir.mkdir(parents=True, exist_ok=True)
    
    orig_path = pathlib.Path(ufile.name)
    ext = orig_path.suffix.lower()
    if allowed_extensions and ext.strip('.') not in allowed_extensions:
        raise ValueError(f"Extension {ext} not allowed. Allowed: {allowed_extensions}")
        
    clean_stem = get_valid_filename(orig_path.stem)
    safe_name = f"{prefix}_{clean_stem}_{uuid.uuid4().hex[:8]}{ext}"
    save_path = upload_dir / safe_name
    
    with open(save_path, 'wb') as fout:
        for chunk in ufile.chunks(chunk_size=4 * 1024 * 1024):  # 4 MB chunks
            fout.write(chunk)
            
    return save_path, f'reports/seminars/{folder_name}/{safe_name}'


@login_required
def seminar_dashboard(request):
    """Lists all Seminar & Event Reports."""
    user_profile = getattr(request.user, 'profile', None)
    role = getattr(user_profile, 'role', 'analytics_team')
    
    if role == 'super_admin':
        reports = SeminarEventReport.objects.all().select_related('college', 'uploaded_by')
    else:
        user_college = getattr(user_profile, 'college', None)
        if user_college:
            reports = SeminarEventReport.objects.filter(college=user_college).select_related('college', 'uploaded_by')
        else:
            reports = SeminarEventReport.objects.none()
            
    return render(request, 'reports/seminar_dashboard.html', {'reports': reports})


@login_required
def create_seminar_report(request):
    """Form and submission handler for recording & analyzing seminars."""
    user_profile = getattr(request.user, 'profile', None)
    role = getattr(user_profile, 'role', 'analytics_team')
    user_college = getattr(user_profile, 'college', None)
    
    if request.method != 'POST':
        # Display the form
        colleges = College.objects.all()
        return render(request, 'reports/create_seminar_report.html', {
            'colleges': colleges,
            'user_college': user_college,
            'is_super_admin': role == 'super_admin'
        })
        
    # Process POST request
    title = request.POST.get('title', '').strip() or 'Seminar Event Report'
    speaker_name = request.POST.get('speaker_name', '').strip()
    date_str = request.POST.get('date', '').strip()
    college_id = request.POST.get('college')
    social_media_posts = request.POST.get('social_media_posts', '').strip()
    transcript_text = request.POST.get('transcript_text', '').strip()
    
    try:
        event_date = date.fromisoformat(date_str) if date_str else date.today()
    except ValueError:
        event_date = date.today()
        
    # Resolve college
    if role == 'super_admin' and college_id:
        college = get_object_or_404(College, id=college_id)
    else:
        college = user_college
        
    if not college:
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': 'College selection is required.'}, status=400)
        messages.error(request, "College is required.")
        return redirect('create_seminar_report')

    # Create the report database entry initially as pending
    report = SeminarEventReport.objects.create(
        title=title,
        college=college,
        date=event_date,
        speaker_name=speaker_name,
        social_media_posts=social_media_posts,
        transcript_text=transcript_text,
        uploaded_by=request.user,
        status='pending'
    )
    
    # Save files
    audio_path_str = None
    document_paths = []
    photo_paths = []
    prefix = f"sem_{report.id}"
    
    try:
        # Save Audio (if recorded or uploaded)
        audio_file = request.FILES.get('audio_file') or request.FILES.get('audio_upload')
        if audio_file:
            path, rel = _save_seminar_file(audio_file, 'audio', prefix, ['webm', 'wav', 'mp3', 'm4a', 'ogg', 'aac'])
            report.audio_file = rel
            audio_path_str = str(path)
            
        # Save Documents (up to 3 PDFs)
        for i in range(1, 4):
            doc_file = request.FILES.get(f'document_file_{i}')
            if doc_file:
                path, rel = _save_seminar_file(doc_file, 'docs', f"{prefix}_doc{i}", ['pdf'])
                setattr(report, f'document_file_{i}', rel)
                document_paths.append(str(path))
                
        # Save Photographs (up to 5 Images)
        for i in range(1, 6):
            photo_file = request.FILES.get(f'photo_{i}')
            if photo_file:
                path, rel = _save_seminar_file(photo_file, 'photos', f"{prefix}_img{i}", ['jpg', 'jpeg', 'png', 'webp'])
                setattr(report, f'photo_{i}', rel)
                photo_paths.append(str(path))
                
        report.save()
        
    except ValueError as e:
        report.delete()
        if request.headers.get('x-requested-with') == 'XMLHttpRequest':
            return JsonResponse({'status': 'error', 'message': str(e)}, status=400)
        messages.error(request, str(e))
        return redirect('create_seminar_report')

    # Dispatch Celery Task
    task = process_seminar_event_report.delay(
        report_id=report.id,
        audio_file_path=audio_path_str,
        document_paths=document_paths,
        photo_paths=photo_paths
    )
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({
            'status': 'success',
            'task_id': task.id,
            'redirect_url': f'/reports/seminar/processing/{task.id}/'
        })
        
    return redirect('seminar_report_processing', task_id=task.id)


@login_required
def seminar_report_processing(request, task_id):
    """Renders loading animation screen while background Celery processing executes."""
    return render(request, 'reports/seminar_report_processing.html', {'task_id': task_id})


@login_required
def check_seminar_task_status(request, task_id):
    """API endpoint to poll Celery task status for the seminar analysis."""
    task_result = AsyncResult(task_id)
    response_data = {
        'state': task_result.state,
        'message': 'Processing media uploads...'
    }
    
    if task_result.state == 'PROGRESS':
        response_data['message'] = task_result.info.get('message', 'Processing...')
    elif task_result.state == 'SUCCESS':
        response_data['message'] = 'Generation completed successfully!'
        response_data.update(task_result.result)  # report_id, redirect_url
    elif task_result.state == 'FAILURE':
        response_data['message'] = 'An error occurred during report generation.'
        response_data['error'] = str(task_result.info)
        
    return JsonResponse(response_data)


@login_required
def preview_seminar_report(request, report_id):
    """Previews the completed seminar analysis report."""
    import re
    report = get_object_or_404(SeminarEventReport, id=report_id)

    # Strip residual markdown code fences Gemini sometimes wraps output with
    summary = report.ai_summary or ''
    summary = re.sub(r'^\s*```html\s*', '', summary.strip(), flags=re.IGNORECASE)
    summary = re.sub(r'\s*```\s*$', '', summary.strip())
    summary = re.sub(r'^\s*```\s*', '', summary.strip())

    # Patch the in-memory object so the template uses cleaned text (does not save to DB)
    report.ai_summary = summary

    return render(request, 'reports/preview_seminar_report.html', {'report': report})
