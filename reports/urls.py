from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_dashboard, name='report_dashboard'),
    path('generate-monthly/', views.generate_monthly, name='generate_monthly'),
    path('generate-quarterly/', views.generate_quarterly, name='generate_quarterly'),
    path('preview/<int:report_id>/', views.preview_monthly, name='preview_monthly'),
    path('preview-quarterly/<int:report_id>/', views.preview_quarterly, name='preview_quarterly'),
]
