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

> **A Django-powered internal platform** for Sarvajanik University to track, manage, and auto-generate PDF/Word/Excel reports from social media analytics, events, newspaper coverage, and press releases — with AI-assisted summaries via Google Gemini.

---

## 🚦 Project Stage

```
Phase 1 ██████████ Complete   ✅  Core data models & admin panel
Phase 2 ██████████ Complete   ✅  Analytics data entry & dashboard
Phase 3 ██████████ Complete   ✅  Monthly & quarterly PDF reports
Phase 4 ██████████ Complete   ✅  Multi-college management & roles
Phase 5 ██████████ Complete   ✅  Annual portfolio, Excel/Word exports & alerts
Phase 6 ░░░░░░░░░░ Planned    📋  Charts, notifications & API
```

**Current Version:** `v3.0.0-beta` · **Stack:** Django 5.2 · SQLite/PostgreSQL · WeasyPrint · Celery · Redis · Gemini AI

---

## ✨ Features

### 📈 Analytics Management
- Enter monthly social media data per college (Instagram, Facebook, YouTube)
- Track views, reach, followers gained, reels count, and graphics count
- PDF extraction — upload a monthly report PDF and let Gemini auto-fill the form
- Submission lifecycle: `pending → submitted → verified` with per-college status tracking
- Export submission status to Excel

### 🗓️ Events Tracking
- Log university events with categories (Workshop, Festival, Placement, Achievement, Conference, Guest Lecture, Academic, Cultural, Sports)
- Attach media files (images, videos, PDFs, reels, posters) to events
- Approval workflow: `pending → confirmed / rejected` with rejection reasons
- Event detail view with all associated media

### 📄 Report Generation
- **Monthly Reports** — HTML-to-PDF per college per month via WeasyPrint
  - Includes analytics, events, top Instagram/Facebook posts, newspaper coverage & press releases
  - Download as PDF or Word (`.docx`)
- **Quarterly Reports** — Aggregated Q1–Q4 summaries across all colleges
  - AI-written narrative summaries powered by **Google Gemini 2.5 Flash**
  - Download as PDF or Word
- **Upload & Condense Reports** — Upload up to 3 monthly PDF reports; Gemini extracts data and generates a full quarterly HTML summary with SVG charts, metric cards, and honest recommendations
  - Async processing via Celery with live progress tracking
  - Download as PDF or Word
- **Annual Portfolio Report** — Full-year consolidated report per college
  - Download as PDF, Word (`.docx`), or Excel (`.xlsx`)
- **Report Comparison** — Side-by-side comparison of any two monthly reports

### 🏫 Multi-College Support
- Role-based access: `Super Admin`, `College Admin`, `Analytics Team`
- College admins see only their own college's data
- Super admins manage all colleges from one dashboard
- University hierarchy: University → College → Department → Programme

### 📊 KPI & Alerts
- Set KPI targets per college/department/programme per year for any metric
- KPI gap analysis view with Excel export
- Automated daily alert scan (via Celery Beat) for:
  - Missing monthly data
  - Large month-over-month swings (>50%)
  - Stale pending submissions
- Alert centre with resolve workflow and manual scan trigger

### 📰 Media & Coverage Tracking
- Newspaper coverage entries (publication, headline, edition, clipping image)
- Press release tracking (title, content, placements, potential reach)

### 🌱 Data Seeding
- `python manage.py seed_data` creates Sarvajanik University, all 8 institutes, SCET departments/programmes, 6 months of dummy analytics, and 6 dummy events per college — fully idempotent
- `python manage.py seed_users` creates one demo user per role with fixed credentials

---

## 🗂️ Project Structure

```
SU_Analytics/
├── accounts/           # Auth, login/logout, user profiles & roles, session timeout
├── analytics_app/      # Monthly analytics, KPI targets, alerts, PDF extraction
│   └── services/       # Alert engine, KPI gap, comparisons, Excel export
├── colleges/           # University → College → Department → Programme models
│   └── management/commands/seed_data.py
├── events/             # Events & media tracking, approval workflow
├── reports/            # All report types: monthly, quarterly, upload-condense, portfolio
│   ├── services/       # PDF, Word, Excel, Gemini, portfolio, rate-limit services
│   └── views/          # monthly, quarterly, upload, portfolio, compare, dashboard
├── su_analytics/       # Django settings, root URLs, Celery config, dashboard view
├── templates/          # All HTML templates
├── static/             # CSS, JS, images
├── entrypoint.sh       # Docker startup: migrate → seed → Redis → Celery → Gunicorn
├── Dockerfile
├── requirements.txt
└── manage.py
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2.1 |
| Database | SQLite (dev) / PostgreSQL (prod via `DATABASE_URL`) |
| PDF Engine | WeasyPrint 68.1 |
| Word Export | python-docx 1.1.2 |
| Excel Export | openpyxl 3.1.5 |
| AI Summaries | Google Gemini 2.5 Flash (`google-genai`) |
| PDF Parsing | pypdf 5.3.0 |
| Image Handling | Pillow 12.2.0 |
| Background Tasks | Celery 5.6.3 + Redis 7.4.0 |
| Static Files | WhiteNoise 6.9.0 |
| WSGI Server | Gunicorn 23.0.0 |
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

Create a `.env` file with:

```bash
GEMINI_API_KEY=your_google_gemini_api_key_here
DJANGO_SECRET_KEY=your_secret_key_here
# Optional: DATABASE_URL=postgres://user:pass@host:5432/dbname
```

> Get your free Gemini API key at [aistudio.google.com](https://aistudio.google.com/apikey).

### 5. Apply Migrations

```bash
python manage.py migrate
```

### 6. Seed Data

```bash
python manage.py seed_data    # University, colleges, departments, dummy analytics & events
python manage.py seed_users   # Demo users for each role
```

### 7. (Optional) Start Redis + Celery for async tasks

```bash
redis-server &
celery -A su_analytics worker --loglevel=info &
celery -A su_analytics beat --loglevel=info &
```

### 8. Run the Development Server

```bash
python manage.py runserver
```

Open your browser at **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🔑 Demo Credentials

| Role | Username | Password |
|---|---|---|
| Super Admin | `super_admin` | `SuperAdmin@123` |
| College Admin | `college_admin` | `CollegeAdmin@123` |
| Analytics Team | `analytics_team` | `Analytics@123` |
| Django Admin | `admin` | `suanalytics2026` *(HF Spaces only)* |

---

## 🔗 URL Routes

| URL | Description |
|---|---|
| `/` | Main dashboard |
| `/accounts/login/` | Login page |
| `/analytics/add/` | Add monthly analytics |
| `/analytics/extract-from-pdf/` | Extract analytics from PDF via Gemini |
| `/analytics/yearly/` | Yearly analytics overview |
| `/analytics/university/` | University hierarchy overview |
| `/analytics/kpi-gap/` | KPI gap analysis |
| `/analytics/submission-status/` | Submission status tracker |
| `/analytics/alerts/` | Alert centre |
| `/events/add/` | Add a new event |
| `/reports/` | Reports dashboard |
| `/reports/generate-monthly/` | Generate monthly PDF |
| `/reports/generate-quarterly/` | Generate quarterly PDF + AI summary |
| `/reports/upload-document/` | Upload PDFs → Gemini condenses → quarterly report |
| `/reports/portfolio/` | Annual portfolio report |
| `/reports/compare/` | Compare two monthly reports |
| `/admin/` | Django admin panel |

---

## 🐳 Docker / Hugging Face Spaces

The app ships as a single Docker container. On every startup `entrypoint.sh` runs:

1. `python manage.py migrate`
2. `python manage.py seed_data` — idempotent; creates colleges, university, dummy data
3. `python manage.py seed_users` — idempotent; creates demo users
4. Starts Redis (in-container broker)
5. Starts Celery worker + Celery Beat scheduler
6. Starts Gunicorn on port `7860`

> **Note:** HF Spaces uses an ephemeral filesystem — `db.sqlite3` resets on every restart. All seed data is recreated automatically. For persistent storage, configure `DATABASE_URL` to point to a PostgreSQL instance (see `POSTGRESQL.md`).

---

## 🛠️ Admin Panel

Access the Django admin at `/admin/` to:

- Manage colleges, users, and roles
- View/edit all analytics entries, events, and reports
- Upload newspaper clippings and manage press releases
- Manage KPI targets and alerts

---

## 🗺️ Upcoming Features (Phase 6+)

- [ ] **Interactive Charts** — Chart.js visualizations on the dashboard
- [ ] **Email Notifications** — Automated monthly reminders to college admins
- [ ] **WhatsApp/Telegram Bot** — Push report notifications via messaging platforms
- [ ] **REST API** — Expose analytics data via DRF for third-party integrations
- [ ] **Bulk Data Import** — CSV/Excel upload for batch analytics entry
- [ ] **Custom Report Templates** — Per-college branded PDF templates
- [ ] **Year-over-Year Comparison** — Multi-year analytics trend views
- [ ] **Mobile-Responsive UI** — Full responsive design revamp
- [ ] **Dark Mode UI** — Full dark-mode support across the platform

---

*Last updated: 18 May 2026*
