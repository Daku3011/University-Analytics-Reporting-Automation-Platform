from datetime import date
from pathlib import Path
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from django.template.loader import render_to_string
from django.conf import settings

from colleges.models import College
from events.models import Event
from analytics_app.models import MonthlyAnalytics, TopPost
from reports.models import MonthlyReport, NewspaperCoverage, PressRelease
from reports.services.pdf_service import PDFService
from reports.services.word_service import build_portfolio_docx, build_monthly_docx

@login_required
def generate_monthly(request):
    if request.method == 'POST':
        college_id = request.POST.get('college')
        month_str = request.POST.get('month')
        year_str = request.POST.get('year')
        report_title = request.POST.get('report_title', '').strip()
        prepared_by = request.POST.get('prepared_by', '').strip()

        if not college_id or not month_str or not year_str:
            messages.error(request, "Missing required parameters: College, Month, or Year.")
            return redirect('report_dashboard')

        try:
            month = int(month_str)
            year = int(year_str)
        except ValueError:
            messages.error(request, "Month and Year must be valid numeric values.")
            return redirect('report_dashboard')

        if not (1 <= month <= 12):
            messages.error(request, "Month must be between 1 and 12.")
            return redirect('report_dashboard')

        if hasattr(request.user, 'profile') and request.user.profile.college:
            college = request.user.profile.college
        else:
            try:
                college = College.objects.get(id=college_id)
            except (College.DoesNotExist, ValueError):
                messages.error(request, "Specified College does not exist.")
                return redirect('report_dashboard')

        analytics = MonthlyAnalytics.objects.filter(college=college, month=month, year=year).first()
        events = Event.objects.filter(college=college, date__month=month, date__year=year)
        top_ig = TopPost.objects.filter(college=college, month=month, year=year, platform='instagram')[:5]
        top_fb = TopPost.objects.filter(college=college, month=month, year=year, platform='facebook')[:5]
        newspapers = NewspaperCoverage.objects.filter(college=college, month=month, year=year)
        press_releases = PressRelease.objects.filter(college=college, month=month, year=year)

        try:
            month_name = date(year, month, 1).strftime('%B')
        except ValueError:
            messages.error(request, "Invalid Year value specified.")
            return redirect('report_dashboard')

        max_views = 1
        if analytics:
            max_views = max(1, analytics.instagram_views, analytics.facebook_views, analytics.total_views)

        # Fall back to sensible defaults if user left fields blank
        if not report_title:
            report_title = f"{college.name} — {month_name} {year} Monthly Report"
        if not prepared_by:
            prepared_by = request.user.get_full_name() or request.user.username

        context = {
            'college': college,
            'month_name': month_name,
            'year': year,
            'analytics': analytics,
            'max_views': max_views,
            'events': events,
            'events_count': events.count(),
            'top_ig': top_ig,
            'top_fb': top_fb,
            'newspapers': newspapers,
            'press_releases': press_releases,
            'report_title': report_title,
            'prepared_by': prepared_by,
        }
        html_string = render_to_string('reports/monthly_report_template.html', context)
        
        try:
            pdf_path = settings.MEDIA_ROOT / 'reports' / 'monthly' / f'{college.code}_{month}_{year}.pdf'
            PDFService.compile_html_to_pdf(html_string, pdf_path)
        except Exception as e:
            messages.error(request, f"PDF compilation failed: {str(e)}")
            return redirect('report_dashboard')

        report, _created = MonthlyReport.objects.update_or_create(
            college=college, month=month, year=year,
            defaults={
                'pdf_file': f'reports/monthly/{college.code}_{month}_{year}.pdf',
                'generated_text': html_string,
                'report_title': report_title,
                'prepared_by': prepared_by,
            }
        )
        # Also generate DOCX
        try:
            docx_path = settings.MEDIA_ROOT / 'reports' / 'monthly' / f'{college.code}_{month}_{year}.docx'
            docx_bytes = build_monthly_docx(
                college, month, year, analytics, events, top_ig, top_fb,
                newspapers, press_releases,
                report_title=report_title, prepared_by=prepared_by,
            )
            with open(docx_path, 'wb') as f:
                f.write(docx_bytes)
        except Exception as e:
            messages.warning(request, f"DOCX generation warning: {str(e)}")
        return redirect('preview_monthly', report_id=report.id)
    return redirect('report_dashboard')


@login_required
def preview_monthly_word(request, report_id):
    """Serve the DOCX download for a monthly report."""
    report = get_object_or_404(MonthlyReport, id=report_id)
    # pdf_file.name is a relative path like 'reports/monthly/SCET_1_2026.pdf'
    # We must prepend MEDIA_ROOT to get the absolute filesystem path
    docx_path = settings.MEDIA_ROOT / Path(report.pdf_file.name).with_suffix('.docx')
    if docx_path.exists():
        docx_bytes = docx_path.read_bytes()
        response = HttpResponse(docx_bytes, content_type=
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document')
        response['Content-Disposition'] = f'attachment; filename=" Monthly_Report_{report.college.code}_{report.month}_{report.year}.docx"'
        return response
    messages.error(request, 'DOCX file not found.')
    return redirect('preview_monthly', report_id=report.id)


@login_required
def preview_monthly(request, report_id):
    report = get_object_or_404(MonthlyReport, id=report_id)
    return render(request, 'reports/preview_monthly.html', {'report': report})
