from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Event, Media
from colleges.models import College
from accounts.decorators import college_queryset_filter, get_user_college, role_required
from su_analytics.constants import EVENT_CATEGORY_CHOICES

ALLOWED_MEDIA_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'pdf'}
MAX_MEDIA_SIZE_MB = 50


@login_required
def add_event(request):
    if request.method == 'POST':
        title = request.POST.get('title', '').strip()
        description = request.POST.get('description', '')
        category = request.POST.get('category', 'other')
        date_str = request.POST.get('date', '')
        college_id = request.POST.get('college')
        social_media_link = request.POST.get('social_media_link', '')

        # ── Input Validation ─────────────────────────────────────────
        if not title:
            messages.error(request, 'Event title is required.')
            return redirect('add_event')

        if not date_str:
            messages.error(request, 'Event date is required.')
            return redirect('add_event')

        valid_categories = [c[0] for c in EVENT_CATEGORY_CHOICES]
        if category not in valid_categories:
            messages.error(request, f'Invalid category. Must be one of: {", ".join(valid_categories)}')
            return redirect('add_event')

        # ── College Assignment (RBAC) ────────────────────────────────
        user_college = get_user_college(request.user)
        if user_college:
            college = user_college
        elif college_id:
            try:
                college = College.objects.get(id=college_id)
            except (College.DoesNotExist, ValueError):
                messages.error(request, 'Selected college does not exist.')
                return redirect('add_event')
        else:
            college = College.objects.first()
            if not college:
                messages.error(request, 'No colleges exist. Create one in the admin panel first.')
                return redirect('add_event')

        event = Event.objects.create(
            college=college,
            title=title,
            description=description,
            category=category,
            date=date_str,
            social_media_link=social_media_link,
            created_by=request.user,
            # approval_status defaults to 'pending' automatically
        )

        # ── Media Upload Validation ──────────────────────────────────
        for f in request.FILES.getlist('media'):
            ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else ''
            if ext not in ALLOWED_MEDIA_EXTENSIONS:
                messages.warning(request, f'Skipped "{f.name}" — unsupported file type.')
                continue
            if f.size > MAX_MEDIA_SIZE_MB * 1024 * 1024:
                messages.warning(request, f'Skipped "{f.name}" — exceeds {MAX_MEDIA_SIZE_MB}MB limit.')
                continue
            Media.objects.create(event=event, file=f)

        messages.success(
            request,
            f'Event "{title}" submitted successfully. It is now pending approval by a super admin.'
        )
        return redirect('event_detail', event_id=event.id)

    # GET: show form
    user_college = get_user_college(request.user)
    colleges = College.objects.filter(id=user_college.id) if user_college else College.objects.all()

    return render(request, 'events/add_event.html', {'colleges': colleges})


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(
        Event.objects.select_related('college', 'created_by', 'reviewed_by').prefetch_related('media'),
        id=event_id
    )

    # RBAC: college admins can only see their college's events
    user_college = get_user_college(request.user)
    if user_college and event.college != user_college:
        messages.error(request, 'You do not have permission to view this event.')
        return redirect('dashboard')

    return render(request, 'events/event_detail.html', {'event': event})


@login_required
def pending_events(request):
    """
    Super-admin view: list all events awaiting approval.
    College admins see only their own college's pending events.
    """
    events = Event.objects.filter(
        approval_status=Event.ApprovalStatus.PENDING
    ).select_related('college', 'created_by').order_by('-created_at')

    user_college = get_user_college(request.user)
    if user_college:
        events = events.filter(college=user_college)

    return render(request, 'events/pending_events.html', {'events': events})


@login_required
@role_required('super_admin')
def confirm_event(request, event_id):
    """Super admin confirms (approves) a pending event."""
    event = get_object_or_404(Event, id=event_id)

    if not event.is_pending:
        messages.warning(request, f'Event "{event.title}" is already {event.get_approval_status_display().lower()}.')
        return redirect('event_detail', event_id=event.id)

    event.confirm(reviewed_by=request.user)
    messages.success(request, f'Event "{event.title}" has been confirmed.')
    return redirect('event_detail', event_id=event.id)


@login_required
@role_required('super_admin')
def reject_event(request, event_id):
    """Super admin rejects a pending event with an optional reason."""
    event = get_object_or_404(Event, id=event_id)

    if not event.is_pending:
        messages.warning(request, f'Event "{event.title}" is already {event.get_approval_status_display().lower()}.')
        return redirect('event_detail', event_id=event.id)

    reason = request.POST.get('reason', '').strip()
    event.reject(reviewed_by=request.user, reason=reason)
    messages.error(request, f'Event "{event.title}" has been rejected.')
    return redirect('event_detail', event_id=event.id)
