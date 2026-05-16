from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from .models import Event, Media

@login_required
def add_event(request):
    if request.method == 'POST':
        from colleges.models import College
        title = request.POST['title']
        description = request.POST.get('description', '')
        category = request.POST['category']
        date = request.POST['date']
        college_id = request.POST.get('college')
        if hasattr(request.user, 'profile') and request.user.profile.college:
            college = request.user.profile.college
        else:
            college = College.objects.get(id=college_id) if college_id else College.objects.first()
        event = Event.objects.create(
            college=college, title=title, description=description,
            category=category, date=date
        )
        for f in request.FILES.getlist('media'):
            Media.objects.create(event=event, file=f)
        return redirect('event_detail', event_id=event.id)
    from colleges.models import College
    colleges = College.objects.all()
    return render(request, 'events/add_event.html', {'colleges': colleges})

@login_required
def event_detail(request, event_id):
    event = get_object_or_404(Event, id=event_id)
    return render(request, 'events/event_detail.html', {'event': event})
