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
- Manual data entry: enter monthly metrics and top posts by hand.
- PDF extraction: convert report PDFs into structured records.
- Events: log university activities and supporting media.
- Reports: generate monthly, quarterly, comparison, and document-based PDFs.
- Media coverage: track newspaper clipping records and press releases.
- Access control: keep data scoped by user role and college.
- Admin panel: full backend management for staff.

## 14. Best Way to Explore the App

If you are new to the platform, start with the dashboard, then move to the yearly overview, then open the reports section. After that, try adding one month of analytics and one event so you can see how the data appears in reports.

Once you understand those flows, the PDF extraction and comparison tools become much easier to use.
