from django.urls import path
from . import views

urlpatterns = [
    path('', views.report_dashboard, name='report_dashboard'),
    path('generate-monthly/', views.generate_monthly, name='generate_monthly'),
    path('generate-quarterly/', views.generate_quarterly, name='generate_quarterly'),
    path('preview/<int:report_id>/', views.preview_monthly, name='preview_monthly'),
    path('preview-quarterly/<int:report_id>/', views.preview_quarterly, name='preview_quarterly'),
    # New: Upload large document → Gemini condenses → quarterly summary PDF
    path('upload-document/', views.upload_document_report, name='upload_document_report'),
    path('preview-document/<int:report_id>/', views.preview_document_report, name='preview_document_report'),
    path('processing/<str:task_id>/', views.document_report_processing, name='document_report_processing'),
    path('processing/status/<str:task_id>/', views.check_task_status, name='check_task_status'),
    path('compare/', views.compare_reports, name='compare_reports'),
]
