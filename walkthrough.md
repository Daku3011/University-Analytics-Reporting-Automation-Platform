# SU Analytics Walkthrough

This document gives a practical tour of the platform and explains the main screens, workflows, and feature groups in simple terms.

## 1. What the Platform Does

SU Analytics is a Django-based internal reporting platform for Sarvajanik University. It brings together social media analytics, event tracking, newspaper coverage, press releases, and PDF report generation in one place.

The app is designed to help teams:

- capture monthly data for each college,
- review yearly performance trends,
- generate monthly and quarterly reports,
- compare report periods,
- and extract report data from uploaded PDFs when manual entry is not convenient.

## 2. Main Navigation Flow

Most users will move through the app in this order:

1. Open the main dashboard.
2. Review totals, recent activity, and yearly performance trends.
3. Go to the yearly dashboard for a college-by-college annual view.
4. Add or extract monthly analytics.
5. Log events and media items.
6. Generate reports from the reports section.
7. Preview and download the generated PDFs.

## 3. Dashboard Overview

The main dashboard is the landing page of the system. It gives a quick snapshot of the current data already stored in the database.

### What you see here

- Total colleges available in the system.
- Total events logged.
- Combined views and reach across analytics records.
- A month-wise chart for the current year.
- Recent event activity.

### Why it matters

This page is the fastest way to understand the current state of the platform. It helps admins and college users see whether data is being updated regularly and whether the year is progressing as expected.

## 4. Yearly Dashboard

The yearly dashboard gives a structured annual view of performance for one college and one selected year.

### What it includes

- Monthly analytics totals across the chosen year.
- A chart for yearly views and reach.
- Event counts and monthly trends.
- Newspaper coverage and press release summaries.
- Top post and content activity where available.

### Why this screen is useful

This is the best screen for annual review meetings. It helps teams spot:

- which months performed strongly,
- which months need attention,
- whether views and reach are rising or falling,
- and whether event or media activity matches the social media output.

## 5. Manual Data Entry

The manual data entry area is used when a user wants to enter analytics by hand rather than extract it from a PDF.

### Main inputs

- College selection.
- Month and year.
- Instagram and Facebook views.
- Instagram and Facebook reach.
- Follower counts and follower growth.
- YouTube subscribers.
- Reel count and graphics count.
- Top Instagram and Facebook posts.

### How it works

When the form is saved, the system updates or creates the monthly analytics record for that college and period. It also stores top posts so those can appear later in previews and reports.

### When to use it

- When data is already prepared by the team.
- When you need quick correction of a specific month.
- When PDF extraction is not needed.

## 6. PDF Extraction Workflow

The app also supports extracting analytics from an uploaded PDF.

### Flow

1. Upload a PDF from the extraction screen.
2. The system sends the file to Gemini for structured extraction.
3. The app detects the likely college, month, year, analytics, top posts, and events.
4. The extracted data is shown in a preview screen.
5. The user confirms or corrects the data.
6. The final records are saved to the database.

### Why this is helpful

This saves time when reports already exist in PDF format and only need to be converted into structured records.

## 7. Events Section

The events module is used to record university activities and their details.

### What can be stored

- Event title and description.
- Category such as workshop, festival, placement, achievement, conference, guest lecture, academic, cultural, or sports.
- Event date.
- Event media links or attachments where supported.

### Event detail page

Each event has a detail view that shows the full event information and related media. This is useful when you need to review the story behind an activity, not just its title.

## 8. Reports Section

The reports area is the center of the platform’s output workflow. It brings together monthly reports, quarterly reports, document-based reports, and comparison tools.

### Report dashboard

The reports landing page lists recent monthly reports, quarterly reports, and uploaded document reports. It acts as a hub for report generation and preview.

### Monthly reports

Monthly reports combine:

- analytics,
- events,
- top Instagram and Facebook posts,
- newspaper coverage,
- and press releases.

The system renders the report as HTML first, then compiles it to PDF and stores the output for preview.

### Quarterly reports

Quarterly reports summarize three months at a time and include an AI-written narrative section. They are meant for higher-level review and are restricted to authorized roles.

### Compare reports

The compare tool lets you put two months side by side for one college. It highlights differences in:

- views,
- reach,
- follower growth,
- content output,
- events,
- newspaper coverage,
- and press release activity.

This is useful when you want to see what changed between two reporting periods.

### Upload document reports

This workflow is for larger source documents. Users can upload multiple PDF reports, and the system processes them asynchronously through Celery before producing a condensed quarterly-style output.

## 9. Media Coverage and Press Releases

The platform also tracks publicity activity outside social media.

### Newspaper coverage

- Store publication details.
- Record headline and edition information.
- Keep clipping images or source references.

### Press releases

- Record release title and content.
- Track placements and reach-related context.

These entries feed into monthly and quarterly report generation so the final PDF reflects the full communication picture, not just social media stats.

## 10. College and Access Control

The app uses role-based access so users do not see data they should not manage.

### Typical roles

- Super Admin: sees everything and manages all colleges.
- College Admin: sees data for their own college.
- Analytics Team: can work with reporting and entry workflows depending on permissions.

### College filtering

Many screens automatically scope data to the logged-in user’s college. That keeps the experience focused and prevents users from editing the wrong institution’s records.

## 11. Admin Panel

The Django admin panel is available for deeper management tasks.

### What it is used for

- Managing colleges and users.
- Reviewing analytics, events, and reports.
- Updating database entries directly when needed.

This is the backend control room for staff who need full access.

## 12. Typical Usage Scenarios

### For a college admin

- Check the dashboard.
- Add monthly analytics or upload a source PDF.
- Add events for the month.
- Generate the monthly report.
- Review the preview before using it elsewhere.

### For a super admin

- Review the yearly dashboard for overall trends.
- Compare two months for one college.
- Generate quarterly summaries.
- Check whether all colleges are keeping their data current.

### For a reporting team member

- Enter or extract data.
- Validate top posts and event entries.
- Generate reports.
- Use previews to verify the final output before sharing.

## 13. Feature Summary

- Dashboard: quick overview of totals, trends, and recent activity.
- Yearly dashboard: annual analytics and college-level trend review.
- KPI Gaps: target vs actual for each metric, with gap and achievement percentage.
- Submission Status: which months are submitted, pending, incomplete, or verified.
- Compare & Trends: year-over-year and institute-wise comparisons with % changes.
- University Explorer: drill from university down to institute, department, and programme.
- Manual data entry: enter monthly metrics and top posts by hand.
- PDF extraction: convert report PDFs into structured records.
- Events: log university activities and supporting media.
- Reports: generate monthly, quarterly, comparison, and document-based PDFs.
- Annual Portfolio: one consolidated per-college report with chapters, downloadable as PDF, Excel, or Word.
- Alert Center: automatic alerts for missing data, stuck submissions, and sudden swings.
- Media coverage: track newspaper clipping records and press releases.
- Access control: keep data scoped by user role and college.
- Admin panel: full backend management for staff.

## 14. Best Way to Explore the App

If you are new to the platform, start with the dashboard, then move to the yearly overview, then open the reports section. After that, try adding one month of analytics and one event so you can see how the data appears in reports.

Once you understand those flows, the PDF extraction and comparison tools become much easier to use.

## 15. KPI Gaps

The KPI Gaps screen compares what each institute planned against what it actually achieved.

### What it shows

- One row per target: the metric, the target value, the actual value, the gap, and the achievement percentage.
- Colour-coded status so it is obvious at a glance which targets are on track and which are behind.
- Targets can exist at college level, department level, or programme level, and the actual numbers always come from the matching scope.

Super admins can switch the filter to "All Colleges" to see a university-wide roll-up grouped institute by institute. Both the on-screen table and the Excel export respect this choice, so what you download is exactly what you see.

### Where to find it

Analytics → KPI Gaps, with an "Export Excel" button next to the filters.

## 16. Submission Status

The Submission Status screen answers a simple question for any college and year: for each of the twelve months, where does the data stand?

### What it shows

- A row per month with its current state: pending, submitted, incomplete, or verified.
- Who submitted the record and when, plus who verified it.
- A green "Export Excel" button so the same grid can be shared offline as a spreadsheet.

College admins see their own institute only; super admins can pick any college. This screen is usually the fastest way to spot which institutes need a reminder.

## 17. Compare & Trends

The Compare & Trends screen has two modes.

### Year-over-year mode

Pick one college (or stay on your own) and compare the selected year against the previous year, month by month:

- Each month shows current vs previous values side by side.
- Percentage changes are colour-coded: green when growing, red when falling.
- A line chart draws both years so the shape of the trend is visible immediately.
- Totals for the year appear at the bottom.

### Institute-wise mode

Super admins can rank every institute on one metric for a chosen year:

- Rows show each college's total, last year's total, the % change, and its share of the university total.
- Colleges are ordered best-first, with rank badges.
- A bar chart compares institutes visually.

College admins get a privacy-friendly version: they see their own college's numbers alongside the university total, average, and their rank — but never other institutes' names or figures.

### Where to find it

Analytics → Compare & Trends (`/analytics/compare/`).

## 18. University Explorer (Drill-Down)

The University Explorer lets you walk down the hierarchy: University → College → Department → Programme.

### How the drill-down works

1. **University Overview** lists every institute as a card with year-to-date views, reach, event count, a data-completeness bar (how many months have been reported out of how many were expected), a change badge versus last year, and department/programme counts. Critical alerts show up here too.
2. **Click a college card** to open its detail page: yearly totals, the departments inside it, and links onward.
3. **Click a department** to see its monthly table and the programmes under it, each linking further down.
4. **Programme pages** show their own monthly rows.

### Important behaviour worth knowing

- Department and programme numbers live in their own separate buckets. Institute-level totals never mix them in, so adding up a college's departments will not accidentally double-count anything.
- Top posts, newspaper coverage, and press releases are recorded at college level, so they appear on the college pages rather than being split per department.

### Data entry follows the hierarchy too

On the Add Analytics form (and the PDF-extraction preview), users can optionally pick a Department and then a Programme. The programme list filters automatically once a department is chosen, and the system validates that everything belongs together before saving. Leaving both blank keeps the record at normal institute level, exactly as before.

### Where to find it

Overview → University Explorer (`/analytics/university/`). Super admins browse every college; college admins land on their own.

## 19. Annual Portfolio Report

The Annual Portfolio is the consolidated answer to "give me everything about this college for this year" — one document with six chapters.

### What is inside

1. **Executive Summary** — year totals with year-over-year changes, activity counts, and overall KPI attainment.
2. **Social Media Performance** — monthly views/reach table, platform totals, and top posts.
3. **Events** — every event with date and category, plus category counts.
4. **Media Coverage** — newspapers and channels.
5. **Press Releases** — releases with placements and reach.
6. **KPI Performance** — target vs actual with achievement bars.

### Three download formats, one preview

The preview page shows all chapters on screen with buttons to download:

- **PDF** — print-ready A4 document with chapter page breaks and page-number footers.
- **Excel (.xlsx)** — one worksheet per chapter.
- **Word (.docx)** — editable document with styled heading chapters and tables.

All three are generated fresh from the same data every time you click, so there is no stored copy to go stale.

### Where to find it

Reports → Annual Portfolio (`/reports/portfolio/`). College admins always preview their own institute; super admins can pick any college and year.

## 20. Quick Excel Exports

Alongside the portfolio, the two analytics tables have one-click Excel downloads:

- **KPI Gaps → Export Excel** — the exact rows currently filtered, including scope type (college / department / programme).
- **Submission Status → Export Excel** — the twelve-month grid with submitter and verifier details.

Both respect the same access rules as the screens themselves: college admins always export their own institute even if another was requested.

## 21. Alert Center

The Alert Center watches the data automatically so nobody has to.

### What triggers an alert

| Situation | Example |
|---|---|
| Missing data | A month that has already passed has no submission for a college. Two-plus missing months raise a warning; three or more raise critical. |
| Stuck submissions | A record left as pending or incomplete long after its month ended. |
| Sudden changes | Views, reach, or followers jumped or dropped sharply compared to the previous month. A very large swing escalates to critical. |

### How it behaves

- Alerts are smart about repeats: the nightly scan updates an existing alert instead of creating a duplicate, and upgrades its severity if things get worse.
- When a problem is fixed, the alert closes itself on the next scan.
- Every night at 08:17 a scheduled job runs the scan and emails a digest of anything new. Super admins receive all alerts; each college admin receives only their own institute's. Without SMTP configured, emails simply print to the console instead.
- A red or orange badge on the sidebar counts your open alerts at all times.

### What you can do here

- Filter by state (open / resolved / all), level, and category.
- Click **Resolve** on anything you have handled manually.
- Super admins can click **Run scan now** to re-check everything immediately instead of waiting for the nightly run.

### Where to find it

System → Alert Center (`/analytics/alerts/`). Available to super admins and college admins.

