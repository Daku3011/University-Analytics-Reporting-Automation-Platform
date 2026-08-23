from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_analytics, name='add_analytics'),
    path('extract-from-pdf/', views.extract_from_pdf, name='extract_from_pdf'),
    path('preview-extracted/', views.preview_extracted_data, name='preview_extracted_data'),
    path('yearly/', views.yearly_overview, name='yearly_overview'),
    path('university/', views.university_overview, name='university_overview'),
    path('university/college/<int:college_id>/', views.college_detail, name='college_detail'),
    path('university/department/<int:department_id>/', views.department_detail, name='department_detail'),
    path('university/programme/<int:programme_id>/', views.programme_detail, name='programme_detail'),
    path('compare/', views.comparison_view, name='comparison_view'),
    path('kpi-gap/', views.kpi_gap_view, name='kpi_gap_view'),
    path('kpi-gap/export/', views.kpi_gap_export, name='kpi_gap_export'),
    path('submission-status/', views.submission_status, name='submission_status'),
    path('submission-status/export/', views.submission_status_export, name='submission_status_export'),
    path('status-update/<int:pk>/', views.update_status, name='update_status'),
]
