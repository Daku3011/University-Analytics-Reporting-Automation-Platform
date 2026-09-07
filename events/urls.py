from django.urls import path
from . import views

urlpatterns = [
    path('add/',                          views.add_event,      name='add_event'),
    path('pending/',                      views.pending_events, name='pending_events'),
    path('<int:event_id>/',               views.event_detail,   name='event_detail'),
    path('<int:event_id>/confirm/',       views.confirm_event,  name='confirm_event'),
    path('<int:event_id>/reject/',        views.reject_event,   name='reject_event'),
]
