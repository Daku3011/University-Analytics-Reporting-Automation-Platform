"""Annual Portfolio Report (#5): preview + PDF / Excel / Word downloads."""
import tempfile
from pathlib import Path

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.template.loader import render_to_string
from django.utils import timezone

from accounts.decorators import get_user_college
from analytics_app.models import MonthlyAnalytics
from colleges.models import College

from ..services.pdf_service import PDFService
from ..services.portfolio_service import build_portfolio_context


def _resolve_college_and_year(request):
    """RBAC-scoped (college, year) for the portfolio — locked users always
    land on their own institute."""
    user_college = get_user_college(request.user)
    if user_college:
        college = user_college
    else:
        college_id = request.GET.get('college')
        if college_id:
            college = College.objects.filter(id=college_id).first()
        else:
            college = College.objects.first()
        if college is None:
            return None, None

    year_str = request.GET.get('year') or (
        request.POST.get('year') if request.method == 'POST' else None)
    try:
        year = int(year_str)
    except (TypeError, ValueError):
        year = timezone.localtime(timezone.now()).year
    return college, year


@login_required
def portfolio_preview(request):
    college, year = _resolve_college_and_year(request)
    if college is None:
        messages.warning(request, 'No institutes exist yet — seed data first.')
        return redirect('report_dashboard')

    colleges = College.objects.all()
    years = sorted(
        set(range(year - 2, year + 1)) |
        set(MonthlyAnalytics.objects.filter(college=college)
            .values_list('year', flat=True)),
        reverse=True)

    context = build_portfolio_context(college, year)
    return render(request, 'reports/portfolio_preview.html', {
        **context,
        'colleges': colleges,
        'years': years,
        'selected_year': year,
        'can_select_college': get_user_college(request.user) is None,
    })


def _portfolio_response(request, fmt):
    college, year = _resolve_college_and_year(request)
    if college is None:
        messages.warning(request, 'No institutes exist yet — seed data first.')
        return redirect('report_dashboard')

    context = build_portfolio_context(college, year)
    stem = f"{college.code}_Annual_Portfolio_{year}"
    extension = {'pdf': 'pdf', 'excel': 'xlsx', 'word': 'docx'}[fmt]

    if fmt == 'pdf':
        html_string = render_to_string('reports/portfolio_pdf.html', {
            **context,
            'selected_year': year,
            'base_url': request.build_absolute_uri('/'),
        })
        try:
            with tempfile.TemporaryDirectory() as tmp:
                pdf_path = Path(tmp) / f'{stem}.pdf'
                PDFService.compile_html_to_pdf(
                    html_string, pdf_path, base_url=request.build_absolute_uri('/'))
                payload = pdf_path.read_bytes()
        except Exception as exc:  # WeasyPrint missing GTK/Pango on some hosts
            messages.error(request, f'PDF compilation failed: {exc}')
            return redirect('portfolio_preview')
        response = HttpResponse(payload, content_type='application/pdf')

    elif fmt == 'excel':
        from ..services.excel_service import build_portfolio_workbook
        response = HttpResponse(
            build_portfolio_workbook(context),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        )

    elif fmt == 'word':
        from ..services.word_service import build_portfolio_docx
        response = HttpResponse(
            build_portfolio_docx(context),
            content_type=(
                'application/vnd.openxmlformats-officedocument.wordprocessingml.document'),
        )
    else:
        return redirect('portfolio_preview')

    response['Content-Disposition'] = f'attachment; filename="{stem}.{extension}"'
    return response


@login_required
def portfolio_pdf(request):
    return _portfolio_response(request, 'pdf')


@login_required
def portfolio_excel(request):
    return _portfolio_response(request, 'excel')


@login_required
def portfolio_word(request):
    return _portfolio_response(request, 'word')
