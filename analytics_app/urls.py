from django.urls import path
from . import views

urlpatterns = [
    path('add/', views.add_analytics, name='add_analytics'),
    path('extract-from-pdf/', views.extract_from_pdf, name='extract_from_pdf'),
    path('preview-extracted/', views.preview_extracted_data, name='preview_extracted_data'),
    path('yearly/', views.yearly_overview, name='yearly_overview'),
    path('kpi-gap/', views.kpi_gap_view, name='kpi_gap_view'),
    path('submission-status/', views.submission_status, name='submission_status'),
    path('status-update/<int:pk>/', views.update_status, name='update_status'),
]
