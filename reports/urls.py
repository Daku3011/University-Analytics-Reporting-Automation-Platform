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
    
    # Annual Category Analyzer routes
    path('annual-analyzer/', views.annual_analyzer_dashboard, name='annual_analyzer'),
    path('annual-analyzer/upload/', views.ajax_upload_batch_file, name='ajax_upload_batch_file'),
    path('annual-analyzer/delete/<int:file_id>/', views.ajax_delete_batch_file, name='ajax_delete_batch_file'),
    path('annual-analyzer/status/', views.ajax_get_batch_files_status, name='ajax_get_batch_files_status'),
    path('annual-analyzer/generate/', views.generate_annual_summary, name='generate_annual_summary'),
    path('annual-analyzer/processing/<str:task_id>/', views.annual_report_processing, name='annual_report_processing'),
    path('annual-analyzer/preview/<int:report_id>/', views.preview_annual_report, name='preview_annual_report'),
]

