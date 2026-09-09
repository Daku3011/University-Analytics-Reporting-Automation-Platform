"""Word (DOCX) export for reports."""

from io import BytesIO

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

BRAND = RGBColor(0x1F, 0x3A, 0x5F)
MUTED = RGBColor(0x66, 0x66, 0x66)


def _fmt(value):
    return f"{value or 0:,}"


def _heading(doc, text, level=1):
    h = doc.add_heading(text, level=level)
    for run in h.runs:
        run.font.color.rgb = BRAND
    return h


def _table(doc, headers, rows, number_cols=()):
    table = doc.add_table(rows=1, cols=len(headers))
    table.style = 'Light Grid Accent 1'
    for i, header in enumerate(headers):
        cell = table.rows[0].cells[i]
        cell.text = header
        for paragraph in cell.paragraphs:
            for run in paragraph.runs:
                run.font.bold = True
                run.font.size = Pt(9.5)
    for row in rows:
        cells = table.add_row().cells
        for i, value in enumerate(row):
            text = _fmt(value) if i in number_cols else str(value)
            cells[i].text = text
            for paragraph in cells[i].paragraphs:
                for run in paragraph.runs:
                    run.font.size = Pt(9.5)
                    if i in number_cols:
                        paragraph.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    return table


def build_portfolio_docx(context):
    """Render the portfolio context into a .docx document, returned as bytes."""
    chapters = context['chapters']
    ex = chapters['executive_summary']
    doc = Document()

    # ── Title block ─────────────────────────────────────────────────
    title = doc.add_heading(f"{context['college_name']}", level=0)
    for run in title.runs:
        run.font.color.rgb = BRAND
    subtitle = doc.add_paragraph(
        f"Annual Portfolio Report — {ex['year']} · Sarvajanik University")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in subtitle.runs:
        run.font.color.rgb = MUTED
        run.font.size = Pt(11)

    # ── Chapter 1: Executive summary ────────────────────────────────
    _heading(doc, '1. Executive Summary')
    doc.add_paragraph(
        f"This report consolidates {ex['year']} communications performance for "
        f"{context['college_name']}: social media output and reach, events, media "
        f"coverage, press releases and progress against KPI targets.")
    _table(
        doc,
        ['Metric', str(ex['prev_year']), str(ex['year']), 'Change'],
        [[m['label'], m['previous'], m['current'],
          '—' if m['change'] is None else f"{m['change']:+.1f}%"] for m in ex['yoy']],
        number_cols=(1, 2),
    )
    facts = [
        ('Events held', str(ex['event_count'])),
        ('Media coverage items', str(ex['media_count'])),
        ('Press releases', str(ex['press_release_count'])),
        ('Top posts', str(ex['top_post_count'])),
        ('Months reported', str(ex['months_reported'])),
        ('KPI targets met', f"{ex['kpi_targets_met']} of {ex['kpi_target_count']}"),
        ('Average KPI attainment',
         '—' if ex['kpi_avg_attainment'] is None else f"{ex['kpi_avg_attainment']}%"),
    ]
    _table(doc, ['Highlights', 'Value'], facts)

    # ── Chapter 2: Social media ────────────────────────────────────
    sm = chapters['social_media']
    _heading(doc, '2. Social Media Performance')
    if sm['monthly']:
        _table(
            doc,
            ['Month', 'Total Views', 'Total Reach', 'Followers Gained', 'Reels', 'Graphics'],
            [[row['record'].get_month_display(), row['record'].total_views,
              row['record'].total_reach, row['record'].followers_gained,
              row['record'].reels_count, row['record'].graphics_count]
             for row in sm['monthly']],
            number_cols=(1, 2, 3, 4, 5),
        )
    else:
        doc.add_paragraph('No monthly analytics were recorded for this year.')
    if sm['top_posts']:
        _heading(doc, 'Top Posts', level=2)
        _table(
            doc,
            ['Month', 'Platform', 'Caption', 'Views', 'Likes'],
            [[p.get_month_display(), p.platform.title(), (p.caption or '—')[:80],
              p.views, p.likes] for p in sm['top_posts']],
            number_cols=(3, 4),
        )

    # ── Chapter 3: Events ──────────────────────────────────────────
    ev = chapters['events']
    _heading(doc, '3. Events')
    if ev['events']:
        category_line = ', '.join(
            f"{name.replace('_', ' ').title()} ×{count}" for name, count in ev['categories'])
        doc.add_paragraph(f"{ev['total']} events recorded — by category: {category_line}.")
        _table(
            doc,
            ['Date', 'Title', 'Category'],
            [[e.date.strftime('%d %b %Y') if e.date else '—', e.title,
              (e.category or 'other').replace('_', ' ').title()] for e in ev['events']],
        )
    else:
        doc.add_paragraph('No events were recorded for this year.')

    # ── Chapter 4: Media coverage ──────────────────────────────────
    mc = chapters['media_coverage']
    _heading(doc, '4. Media Coverage')
    if mc['newspapers']:
        _heading(doc, 'Newspapers', level=2)
        _table(
            doc,
            ['Publication', 'Date', 'Headline'],
            [[n.publication, n.date.strftime('%d %b %Y') if n.date else '—',
              n.headline or '—'] for n in mc['newspapers']],
        )
    if mc['channels']:
        _heading(doc, 'TV / Channels', level=2)
        _table(
            doc,
            ['Channel', 'Month', 'Programme / Platform'],
            [[c_.channel_name, f"{c_.month}/{c_.year}", c_.platform or '—']
             for c_ in mc['channels']],
        )
    if not mc['newspapers'] and not mc['channels']:
        doc.add_paragraph('No media coverage was recorded for this year.')

    # ── Chapter 5: Press releases ──────────────────────────────────
    pr = chapters['press_releases']
    _heading(doc, '5. Press Releases')
    if pr['releases']:
        doc.add_paragraph(
            f"{pr['total']} releases issued with {pr['total_placements']} total placements.")
        _table(
            doc,
            ['Date', 'Title', 'Placements', 'Reach'],
            [[p.date_submitted.strftime('%d %b %Y') if p.date_submitted else '—',
              p.title, p.placements, str(p.potential_reach or '—')]
             for p in pr['releases']],
            number_cols=(2,),
        )
    else:
        doc.add_paragraph('No press releases were issued this year.')

    # ── Chapter 6: KPI performance ─────────────────────────────────
    kpi = chapters['kpi_performance']['rows']
    _heading(doc, '6. KPI Performance')
    if kpi:
        _table(
            doc,
            ['Scope', 'Metric', 'Target', 'Actual', 'Gap', 'Achievement'],
            [[str(r_['scope']), r_['metric'], r_['target'], r_['actual'], r_['gap'],
              f"{r_['achievement']}% {'✔' if r_['on_track'] else '✖'}"]
             for r_ in kpi],
            number_cols=(2, 3, 4),
        )
    else:
        doc.add_paragraph('No KPI targets were defined for this year.')

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def build_monthly_docx(college, month, year, analytics, events, top_ig, top_fb,
                       newspapers, press_releases,
                       report_title='', prepared_by=''):
    """Render monthly report data into a .docx document, returned as bytes."""
    from datetime import date as _date
    month_name = _date(year, month, 1).strftime('%B')

    # Sensible defaults if caller didn't pass values
    if not report_title:
        report_title = f"{college.name} — {month_name} {year} Monthly Report"
    if not prepared_by:
        prepared_by = college.name

    doc = Document()

    # ── Cover page ──────────────────────────────────────────────────
    title_para = doc.add_heading(report_title, level=0)
    title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in title_para.runs:
        run.font.color.rgb = BRAND

    sub = doc.add_paragraph(f"Sarvajanik University  ·  {college.name}")
    sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in sub.runs:
        run.font.color.rgb = MUTED
        run.font.size = Pt(11)

    meta = doc.add_paragraph(
        f"Reporting Period: {month_name} {year}     |     Prepared by: {prepared_by}"
    )
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in meta.runs:
        run.font.color.rgb = MUTED
        run.font.size = Pt(10)

    doc.add_page_break()

    # ── Summary section ─────────────────────────────────────────────
    doc.add_paragraph(f"Reporting period: {month_name} {year}")
    doc.add_paragraph(f"Events: {events.count()}")
    doc.add_paragraph(f"Press releases: {press_releases.count()}")

    # ── Analytics table ─────────────────────────────────────────────
    doc.add_heading('Analytics', level=2)
    if analytics:
        _table(doc, ['Metric', 'Value'],
               [['Instagram Views', analytics.instagram_views],
                ['Facebook Views', analytics.facebook_views],
                ['Total Views', analytics.total_views],
                ['Instagram Reach', analytics.instagram_reach],
                ['Facebook Reach', analytics.facebook_reach],
                ['Followers Gained', analytics.followers_gained],
                ['Reels Count', analytics.reels_count],
                ['Graphics Count', analytics.graphics_count],
                ['YouTube Subscribers', analytics.youtube_subscribers],
                ['Instagram Followers', analytics.instagram_followers],
                ['Facebook Followers', analytics.facebook_followers]],
               number_cols=(1,))
    else:
        doc.add_paragraph('No analytics data available.')

    # ── Events ─────────────────────────────────────────────────────
    doc.add_heading('Events', level=2)
    if events:
        for e in events:
            doc.add_paragraph(f"{e.date.strftime('%d %b %Y') if e.date else '—':} — {e.title}")
    else:
        doc.add_paragraph('No events recorded.')

    # ── Press Releases ─────────────────────────────────────────────
    doc.add_heading('Press Releases', level=2)
    if press_releases:
        for p in press_releases:
            doc.add_paragraph(f"{p.date_submitted.strftime('%d %b %Y') if p.date_submitted else '—':} — {p.title}")
    else:
        doc.add_paragraph('No press releases issued.')

    # ── Top Posts ──────────────────────────────────────────────────
    doc.add_heading('Top Posts', level=2)
    if top_ig:
        doc.add_paragraph(f"Instagram:")
        for p in top_ig[:3]:
            doc.add_paragraph(f"{p.get_month_display()} — {p.views} views, {p.likes} likes")
    if top_fb:
        doc.add_paragraph(f"Facebook:")
        for p in top_fb[:3]:
            doc.add_paragraph(f"{p.get_month_display()} — {p.views} views, {p.likes} likes")

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def build_quarterly_docx(college, quarter, year, analytics_by_month,
                         comparison, all_events_count, all_prev_events_count,
                         newspapers_count, prev_newspapers_count,
                         press_releases_count, prev_press_releases_count,
                         all_top_ig, all_top_fb, prev_top_ig, prev_top_fb,
                         month_names):
    """Render quarterly report data into a .docx document, returned as bytes."""
    doc = Document()

    # ── Title block ─────────────────────────────────────────────────
    college_label = college.name if college else 'Sarvajanik University'
    title = doc.add_heading(f"{college_label} — Q{quarter} {year} Quarterly Report", level=0)
    for run in title.runs:
        run.font.color.rgb = BRAND
    subtitle = doc.add_paragraph(f"College: {college.name}")
    subtitle.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in subtitle.runs:
        run.font.color.rgb = MUTED
        run.font.size = Pt(11)

    # ── Quarter overview ────────────────────────────────────────────
    doc.add_heading('1. Quarter Overview', level=2)
    start_month = {1: 1, 2: 4, 3: 7, 4: 10}[quarter]
    m_names = [date(year, m, 1).strftime('%B') for m in range(start_month, start_month + 3)]
    doc.add_paragraph(f"Months covered: {', '.join(m_names)}")

    # ── Comparison ──────────────────────────────────────────────────
    doc.add_heading('2. Year-over-Year Comparison', level=2)
    for key, data in comparison.items():
        pct_str = f"{data['pct']:.1f}%" if data['pct'] is not None else 'N/A'
        doc.add_paragraph(f"{key}: Current {data['current']} vs Previous {data['previous']} (diff: {data['diff']}, {pct_str} change)")

    # ── Best/Worst month ───────────────────────────────────────────
    doc.add_heading('3. Best vs Worst Month', level=2)
    # Find month with highest/lowest values
    for key in ['instagram_views', 'facebook_views', 'total_views']:
        month_data = analytics_by_month.get(key, {})
        if month_data:
            best_month = max(month_data, key=lambda m: month_data[m]['current'])
            worst_month = min(month_data, key=lambda m: month_data[m]['current'])
            doc.add_paragraph(f"{key}: Best {best_month} ({month_data[best_month]['current']}), Worst {worst_month} ({month_data[worst_month]['current']})")

    # ── Platform comparison ─────────────────────────────────────────
    doc.add_heading('4. Platform Comparison — Instagram vs Facebook', level=2)
    doc.add_paragraph(f"Instagram total views: {sum(m.get('instagram_views', {}).get('current', 0) for m in analytics_by_month.values())}")
    doc.add_paragraph(f"Facebook total views: {sum(m.get('facebook_views', {}).get('current', 0) for m in analytics_by_month.values())}")

    # ── Events, Media & Press ───────────────────────────────────────
    doc.add_heading('5. Events, Media & Press Activity', level=2)
    doc.add_paragraph(f"Events — {year}: {all_events_count}, {year-1}: {all_prev_events_count}")
    doc.add_paragraph(f"Newspaper coverage — {year}: {newspapers_count}, {year-1}: {prev_newspapers_count}")
    doc.add_paragraph(f"Press releases — {year}: {press_releases_count}, {year-1}: {prev_press_releases_count}")

    # ── Engagement & Content Trends ─────────────────────────────────
    doc.add_heading('6. Engagement & Content Trends', level=2)
    for key in ['instagram_views', 'facebook_views']:
        month_data = analytics_by_month.get(key, {})
        if month_data:
            total = sum(m.get('current', 0) for m in month_data.values())
            doc.add_paragraph(f"{key.title()}: {total} total across {len(month_data)} months")

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def build_document_docx(title, quarter, year, ai_summary):
    """Render document report data into a .docx document, returned as bytes."""
    from docx import Document
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.shared import Pt, RGBColor

    BRAND = RGBColor(0x1F, 0x3A, 0x5F)
    MUTED = RGBColor(0x66, 0x66, 0x66)

    doc = Document()

    # ── Title block ─────────────────────────────────────────────────
    title_heading = doc.add_heading(title, level=0)
    for run in title_heading.runs:
        run.font.color.rgb = BRAND
    meta = doc.add_paragraph(f"Quarter {quarter} {year}")
    meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
    for run in meta.runs:
        run.font.color.rgb = MUTED
        run.font.size = Pt(11)

    # ── AI Summary ──────────────────────────────────────────────────
    doc.add_heading('AI-Generated Summary', level=2)
    doc.add_paragraph(ai_summary)

    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
