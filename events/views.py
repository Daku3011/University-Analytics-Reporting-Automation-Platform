from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from .models import Event, Media
from colleges.models import College
from accounts.decorators import college_queryset_filter, get_user_college
from su_analytics.constants import EVENT_CATEGORY_CHOICES


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
            # College admins can only add events for their own college
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
            college=college, title=title, description=description,
            category=category, date=date_str,
            social_media_link=social_media_link
        )

        # ── Media Upload Validation ──────────────────────────────────
        ALLOWED_MEDIA_EXTENSIONS = {'jpg', 'jpeg', 'png', 'gif', 'webp', 'mp4', 'mov', 'pdf'}
        MAX_MEDIA_SIZE_MB = 50

        for f in request.FILES.getlist('media'):
            ext = f.name.rsplit('.', 1)[-1].lower() if '.' in f.name else ''
            if ext not in ALLOWED_MEDIA_EXTENSIONS:
                messages.warning(request, f'Skipped "{f.name}" — unsupported file type.')
                continue
            if f.size > MAX_MEDIA_SIZE_MB * 1024 * 1024:
                messages.warning(request, f'Skipped "{f.name}" — exceeds {MAX_MEDIA_SIZE_MB}MB limit.')
                continue
            Media.objects.create(event=event, file=f)

        messages.success(request, f'Event "{title}" created successfully.')
        return redirect('event_detail', event_id=event.id)

    # GET: show form
    user_college = get_user_college(request.user)
    if user_college:
        colleges = College.objects.filter(id=user_college.id)
    else:
        colleges = College.objects.all()

    return render(request, 'events/add_event.html', {'colleges': colleges})


@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)

    # RBAC: college admins can only see their college's events
    user_college = get_user_college(request.user)
    if user_college and event.college != user_college:
        messages.error(request, 'You do not have permission to view this event.')
        return redirect('dashboard')

    return render(request, 'events/event_detail.html', {'event': event})
