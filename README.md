---
title: SU Analytics
emoji: 📊
colorFrom: purple
colorTo: indigo
sdk: docker
pinned: false
license: mit
app_port: 7860
---

# 📊 SU Analytics — University Analytics Reporting Platform

> **A Django-powered internal platform** for Sarvajanik University to track, manage, and auto-generate PDF reports from social media analytics, events, newspaper coverage, and press releases — with AI-assisted quarterly summaries via Google Gemini.

---

## 🚦 Project Stage

```
Phase 1 ██████████ Complete   ✅  Core data models & admin panel
Phase 2 ██████████ Complete   ✅  Analytics data entry & dashboard
Phase 3 ██████████ Complete   ✅  Monthly & quarterly PDF reports
Phase 4 ██████░░░░ In Progress 🔧  Multi-college management & roles
Phase 5 ░░░░░░░░░░ Planned    📋  Charts, exports & notifications
```

**Current Version:** `v0.4-alpha` · **Stack:** Django 5.2 · SQLite · WeasyPrint · Gemini AI

---

## ✨ Features

### 📈 Analytics Management
- Enter monthly social media data per college (Instagram, Facebook, YouTube)
- Track views, reach, followers gained, reels count, and graphics count
- Auto-calculate totals and display them on the dashboard

### 🗓️ Events Tracking
- Log university events with categories (Workshop, Festival, Placement, Achievement, Conference, Guest Lecture, Academic, Cultural, Sports)
- Attach media files (images, videos, PDFs, reels, posters) to events
- Event detail view with all associated media

### 📄 Report Generation
- **Monthly Reports** — HTML-to-PDF reports per college per month using WeasyPrint
  - Includes analytics, events, top Instagram/Facebook posts, newspaper coverage & press releases
- **Quarterly Reports** — Aggregated Q1–Q4 summaries across all colleges
  - AI-written narrative summaries powered by **Google Gemini 2.0 Flash**
- Preview generated reports in-browser before downloading

### 🏫 Multi-College Support
- Role-based access: `Super Admin`, `College Admin`, `Analytics Team`
- College admins see only their own college's data
- Super admins manage all colleges from one dashboard

### 📰 Media & Coverage Tracking
- Newspaper coverage entries (publication, headline, edition, clipping image)
- Press release tracking (title, content, placements, potential reach)

### 🌱 Demo Data Seeding
- One-command seed with real Sarvajanik University data (Jan–Mar 2026)
- Includes 33 events, 3 months of analytics, and 30 top posts

---

## 🗂️ Project Structure

```
SU_Analytics/
├── accounts/           # Auth, login/logout, user profiles & roles
├── analytics_app/      # Monthly analytics data entry & models
├── colleges/           # College model + seed_data management command
├── events/             # Events & media tracking
├── reports/            # PDF generation (monthly + quarterly), newspaper, press release
├── su_analytics/       # Django project settings, root URLs, dashboard view
├── templates/          # All HTML templates
│   ├── accounts/
│   ├── analytics_app/
│   ├── events/
│   └── reports/
├── static/             # CSS, JS, images
├── manage.py
├── requirements.txt
└── .gitignore
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2.14 |
| Database | SQLite (dev) |
| PDF Engine | WeasyPrint 68.1 |
| AI Summaries | Google Gemini 2.0 Flash (`google-generativeai` 0.8.6) |
| Image Handling | Pillow 12.2.0 |
| Frontend | HTML5 · Vanilla CSS · JavaScript |

---

## 🚀 Getting Started

### 1. Clone the Repository

```bash
git clone https://github.com/Daku3011/University-Analytics-Reporting-Automation-Platform.git
cd University-Analytics-Reporting-Automation-Platform
```

### 2. Create a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

> **Note:** WeasyPrint requires system fonts & Cairo. On Ubuntu/Debian:
> ```bash
> sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2
> ```

### 4. Configure Environment Variables

Create a `.env` file (or export directly) with:

```bash
export GEMINI_API_KEY="your_google_gemini_api_key_here"
```

> Get your free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).

### 5. Apply Migrations

```bash
python manage.py migrate
```

### 6. Create a Superuser

```bash
python manage.py createsuperuser
```

### 7. (Optional) Load Demo Data

Seed the database with real Sarvajanik University data from Jan–Mar 2026:

```bash
python manage.py seed_data
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🔑 Default URL Routes

| URL | Description |
|---|---|
| `/` | Main dashboard |
| `/accounts/login/` | Login page |
| `/analytics/add/` | Add monthly analytics |
| `/events/add/` | Add a new event |
| `/reports/` | Reports dashboard |
| `/reports/generate/monthly/` | Generate monthly PDF |
| `/reports/generate/quarterly/` | Generate quarterly PDF + AI summary |
| `/admin/` | Django admin panel |

---

## 🛠️ Admin Panel

Access the Django admin at `/admin/` with your superuser credentials to:

- Manage colleges, users, and roles
- View/edit all analytics entries, events, and reports
- Upload newspaper clippings and manage press releases

---

## 🗺️ Upcoming Features

### 🔜 Coming Soon (Phase 5)

- [ ] **Interactive Charts** — Chart.js visualizations on the dashboard (bar, line, pie)
- [ ] **Excel/CSV Export** — Download analytics data in spreadsheet format
- [ ] **Email Notifications** — Automated monthly reminders to college admins
- [ ] **Dark Mode UI** — Full dark-mode support across the platform

### 📋 Planned (Phase 6+)

- [ ] **WhatsApp/Telegram Bot** — Push report notifications via messaging platforms
- [ ] **REST API** — Expose analytics data via DRF for third-party integrations
- [ ] **PostgreSQL Migration** — Upgrade from SQLite for production deployment
- [ ] **Bulk Data Import** — CSV/Excel upload for batch analytics entry
- [ ] **Custom Report Templates** — Per-college branded PDF templates
- [ ] **Year-over-Year Comparison** — Multi-year analytics trend views
- [ ] **Mobile-Responsive UI** — Full responsive design revamp
- [ ] **Deployment** — Docker + Gunicorn + Nginx production setup

---

*Last updated: 7:45 PM  17 May 2026*
