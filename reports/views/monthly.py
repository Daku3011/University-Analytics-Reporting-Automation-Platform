from datetime import date
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.template.loader import render_to_string
from django.conf import settings

from colleges.models import College
from events.models import Event
from analytics_app.models import MonthlyAnalytics, TopPost
from reports.models import MonthlyReport, NewspaperCoverage, PressRelease
from reports.services.pdf_service import PDFService

@login_required
def generate_monthly(request):
    if request.method == 'POST':
        college_id = request.POST.get('college')
        month_str = request.POST.get('month')
        year_str = request.POST.get('year')

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
            }
        )
        return redirect('preview_monthly', report_id=report.id)
    return redirect('report_dashboard')


@login_required
def preview_monthly(request, report_id):
    report = get_object_or_404(MonthlyReport, id=report_id)
    return render(request, 'reports/preview_monthly.html', {'report': report})
