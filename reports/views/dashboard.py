from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from colleges.models import College
from reports.models import MonthlyReport, QuarterlyReport, UploadedDocumentReport

@login_required
def report_dashboard(request):
    monthly_reports = MonthlyReport.objects.select_related('college').all().order_by('-created_at')[:20]
    quarterly_reports = QuarterlyReport.objects.all().order_by('-created_at')[:10]
    doc_reports = UploadedDocumentReport.objects.all().order_by('-created_at')[:10]
    colleges = College.objects.all()
    months = range(1, 13)
    return render(request, 'reports/report_dashboard.html', {
        'monthly_reports': monthly_reports,
        'quarterly_reports': quarterly_reports,
        'doc_reports': doc_reports,
        'colleges': colleges,
        'months': months,
    })
