from datetime import date
from django.core.management.base import BaseCommand
from colleges.models import College, Department, Programme, University
from events.models import Event
from analytics_app.models import MonthlyAnalytics, TopPost, KpiTarget
from reports.models import NewspaperCoverage, PressRelease

COLLEGES = [
    {"code": "SCET",  "name": "Sarvajanik College of Engineering & Technology"},
    {"code": "SRLIM", "name": "S. R. Luthra Institute of Management"},
    {"code": "SRKI",  "name": "Shree Ramkrishna Institute of Computer Education & Applied Sciences"},
    {"code": "SCCCA", "name": "Sarvajanik College of Commerce & Computer Applications"},
    {"code": "BRCM",  "name": "B. R. C. M. College of Business Administration"},
    {"code": "SCL",   "name": "Sarvajanik College of Law"},
    {"code": "SCOPA", "name": "Shri Pankaj Kapadia Sarvajanik College of Performing Arts"},
    {"code": "SCLA",  "name": "Sarvajanik College of Liberal Arts"},
]

EVENTS_2025 = [
    {"month": 1, "day": 8, "title": "New Year Campaign 2025", "category": "other"},
    {"month": 1, "day": 15, "title": "Workshop on Emerging AI Trends", "category": "workshop"},
    {"month": 1, "day": 22, "title": "3rd Convocation Ceremony", "category": "academic"},
    {"month": 1, "day": 28, "title": "Republic Day Celebration", "category": "cultural"},
    {"month": 2, "day": 5, "title": "SU Carnival 2025 Kickoff", "category": "festival"},
    {"month": 2, "day": 12, "title": "National-Level Debate Competition", "category": "conference"},
    {"month": 2, "day": 20, "title": "Surat Art Street 2025", "category": "cultural"},
    {"month": 2, "day": 27, "title": "Guest Lecture on Digital Marketing", "category": "guest_lecture"},
    {"month": 3, "day": 5, "title": "Mental Health Awareness Workshop", "category": "workshop"},
    {"month": 3, "day": 12, "title": "Entrepreneurship Summit", "category": "conference"},
    {"month": 3, "day": 20, "title": "Faculty Development Program", "category": "workshop"},
    {"month": 3, "day": 28, "title": "Annual Cultural Fest - Samanvay 2025", "category": "festival"},
]

EVENTS = [
    {"month": 1, "day": 6, "title": "New Year Posts", "category": "other"},
    {"month": 1, "day": 13, "title": "Bird Rescue Training Program | SU-Nature Club", "category": "workshop"},
    {"month": 1, "day": 13, "title": "SCET Organises One-Day AI Conclave with Industry Experts", "category": "conference"},
    {"month": 1, "day": 21, "title": "Cyber Security in the Era of AI", "category": "workshop"},
    {"month": 1, "day": 23, "title": "4th Convocation Ceremony - Awards Degrees to Over 2,000 Students", "category": "academic"},
    {"month": 1, "day": 27, "title": "Two-Day R&D Awareness and Capacity Building Workshop", "category": "workshop"},
    {"month": 1, "day": 28, "title": "SCCCA Professor Completes Official Statistics Training at NSSTA", "category": "achievement"},
    {"month": 1, "day": 29, "title": "Third Student Conference on Atmanirbhar Bharat", "category": "conference"},
    {"month": 2, "day": 1, "title": "SU Carnival 2026 Posts Begin", "category": "festival"},
    {"month": 2, "day": 11, "title": "SU Carnival 2026 - Grand Confluence of Culture, Creativity & Learning", "category": "festival"},
    {"month": 2, "day": 17, "title": "Sarvajanik University brings home 1st Prize at IIM-B Plan Competition", "category": "achievement"},
    {"month": 2, "day": 17, "title": "Celebrating 150 Years of Vande Mataram", "category": "cultural"},
    {"month": 2, "day": 21, "title": "Surat Art Street 2026 - Two-Day Celebration at SCET Amphitheatre", "category": "cultural"},
    {"month": 2, "day": 25, "title": "SUMUN 2.0 - Sarvajanik University Hosts Grand Model United Nations Conference", "category": "conference"},
    {"month": 2, "day": 26, "title": "SRLIM Organizes Stractical - The Startup Battle National-Level Competition", "category": "conference"},
    {"month": 3, "day": 6, "title": "BRCM College - Power of Emotions in Positive Mental Health", "category": "workshop"},
    {"month": 3, "day": 10, "title": "Samantvam - Gender Sensitisation Programme by Women Development Cell", "category": "workshop"},
    {"month": 3, "day": 11, "title": "BRCM Guest Lecture on Display Advertising for SYBBA", "category": "guest_lecture"},
    {"month": 3, "day": 12, "title": "BRCM Guest Lecture on Search Engine Advertising", "category": "guest_lecture"},
    {"month": 3, "day": 13, "title": "Google Workspace FDP - Empowering Faculty with Digital Skills", "category": "workshop"},
    {"month": 3, "day": 16, "title": "BRCM College organized Bizz Stratathon", "category": "academic"},
    {"month": 3, "day": 17, "title": "SCOL Session with DLSA Surat", "category": "workshop"},
    {"month": 3, "day": 24, "title": "MoU with India Accelerator to Boost Startup Ecosystem", "category": "achievement"},
    {"month": 3, "day": 25, "title": "Fulbright-Nehru Fellowship Opportunities Session 2027-28", "category": "academic"},
    {"month": 3, "day": 27, "title": "Sanskrit Short Film Training Workshop at Chunilal Gandhi Vidyabhavan", "category": "workshop"},
    {"month": 3, "day": 30, "title": "Samanvay-26 - Annual Function of BRCM College", "category": "festival"},
]

ANALYTICS_DATA = [
    {"month": 1, "year": 2025, "ig_views": 215000, "fb_views": 38200, "yt_views": 380, "total_views": 253200, "ig_reach": 14200, "fb_reach": 11800, "total_reach": 26000, "ig_followers": 120, "fb_followers": 0, "yt_subs": 14, "gained": 148, "reels": 1, "graphics": 30},
    {"month": 2, "year": 2025, "ig_views": 445000, "fb_views": 28200, "yt_views": 290, "total_views": 473490, "ig_reach": 42800, "fb_reach": 8200, "total_reach": 51000, "ig_followers": 340, "fb_followers": 0, "yt_subs": 20, "gained": 360, "reels": 11, "graphics": 25},
    {"month": 3, "year": 2025, "ig_views": 182000, "fb_views": 21800, "yt_views": 230, "total_views": 203800, "ig_reach": 15200, "fb_reach": 6000, "total_reach": 21200, "ig_followers": 85, "fb_followers": 0, "yt_subs": 12, "gained": 100, "reels": 0, "graphics": 21},
    {"month": 1, "year": 2026, "ig_views": 283200, "fb_views": 47300, "yt_views": 463, "total_views": 330900, "ig_reach": 18500, "fb_reach": 14400, "total_reach": 32900, "ig_followers": 155, "fb_followers": 0, "yt_subs": 18, "gained": 193, "reels": 2, "graphics": 37},
    {"month": 2, "year": 2026, "ig_views": 587200, "fb_views": 34500, "yt_views": 350, "total_views": 622050, "ig_reach": 56100, "fb_reach": 10100, "total_reach": 66200, "ig_followers": 432, "fb_followers": 0, "yt_subs": 26, "gained": 460, "reels": 15, "graphics": 30},
    {"month": 3, "year": 2026, "ig_views": 235200, "fb_views": 27100, "yt_views": 282, "total_views": 262300, "ig_reach": 19900, "fb_reach": 7400, "total_reach": 27300, "ig_followers": 111, "fb_followers": 0, "yt_subs": 16, "gained": 130, "reels": 0, "graphics": 26},
]

TOP_POSTS = {
    1: {
        "instagram": [{"views": 17100, "likes": 291, "shares": 161}, {"views": 12600, "likes": 257, "shares": 135}, {"views": 11200, "likes": 213, "shares": 68}, {"views": 8500, "likes": 217, "shares": 124}, {"views": 7200, "likes": 157, "shares": 27}],
        "facebook": [{"views": 13200, "likes": 203}, {"views": 10900, "likes": 96}, {"views": 7100, "likes": 125}, {"views": 8400, "likes": 164}, {"views": 1600, "likes": 27}],
    },
    2: {
        "instagram": [{"views": 43800, "likes": 896, "shares": 267}, {"views": 37600, "likes": 1500, "shares": 525}, {"views": 20900, "likes": 495, "shares": 521}, {"views": 18100, "likes": 334, "shares": 91}, {"views": 15600, "likes": 605, "shares": 104}],
        "facebook": [{"views": 16600, "likes": 487}, {"views": 9800, "likes": 362}, {"views": 7400, "likes": 127}, {"views": 18100, "likes": 334}, {"views": 10300, "likes": 201}],
    },
    3: {
        "instagram": [{"views": 11700, "likes": 141, "shares": 0}, {"views": 8700, "likes": 113, "shares": 0}, {"views": 7300, "likes": 178, "shares": 0}, {"views": 8000, "likes": 140, "shares": 0}, {"views": 5700, "likes": 95, "shares": 0}],
        "facebook": [{"views": 8000, "likes": 140}, {"views": 5800, "likes": 34}, {"views": 6400, "likes": 106}, {"views": 3300, "likes": 44}, {"views": 2900, "likes": 24}],
    },
}

TOP_POSTS_2025 = {
    1: {
        "instagram": [{"views": 13200, "likes": 220, "shares": 110}, {"views": 9800, "likes": 195, "shares": 90}, {"views": 8100, "likes": 160, "shares": 45}],
        "facebook": [{"views": 10100, "likes": 150}, {"views": 7800, "likes": 72}, {"views": 5200, "likes": 88}],
    },
    2: {
        "instagram": [{"views": 32000, "likes": 720, "shares": 210}, {"views": 28000, "likes": 1100, "shares": 400}, {"views": 15500, "likes": 380, "shares": 380}],
        "facebook": [{"views": 12000, "likes": 350}, {"views": 7200, "likes": 260}, {"views": 5400, "likes": 95}],
    },
    3: {
        "instagram": [{"views": 8800, "likes": 105, "shares": 0}, {"views": 6200, "likes": 85, "shares": 0}, {"views": 5100, "likes": 130, "shares": 0}],
        "facebook": [{"views": 5800, "likes": 100}, {"views": 4200, "likes": 28}, {"views": 4800, "likes": 78}],
    },
}

NEWSPAPER_DATA = [
    {"month": 1, "year": 2025, "publication": "Times of India", "date": "2025-01-15", "headline": "Sarvajanik University launches AI Research Center"},
    {"month": 1, "year": 2025, "publication": "Gujarat Samachar", "date": "2025-01-22", "headline": "SU students win National Robotics Competition"},
    {"month": 2, "year": 2025, "publication": "Times of India", "date": "2025-02-10", "headline": "SU Carnival 2025 draws record attendance"},
    {"month": 2, "year": 2025, "publication": "Sandesh", "date": "2025-02-18", "headline": "Sarvajanik University ranks among top 50"},
    {"month": 3, "year": 2025, "publication": "Gujarat Samachar", "date": "2025-03-05", "headline": "SU signs MoU with international university"},
    {"month": 1, "year": 2026, "publication": "Times of India", "date": "2026-01-10", "headline": "SU ranks in top 50 of NIRF Rankings"},
    {"month": 1, "year": 2026, "publication": "Gujarat Samachar", "date": "2026-01-18", "headline": "AI Conclave at SCET sees huge turnout"},
    {"month": 2, "year": 2026, "publication": "Times of India", "date": "2026-02-12", "headline": "SU Carnival 2026 - A Grand Success"},
    {"month": 2, "year": 2026, "publication": "Sandesh", "date": "2026-02-20", "headline": "SU students win IIM-B Plan Competition"},
    {"month": 2, "year": 2026, "publication": "Gujarat Samachar", "date": "2026-02-25", "headline": "SUMUN 2.0 concludes successfully"},
    {"month": 3, "year": 2026, "publication": "Times of India", "date": "2026-03-08", "headline": "BRCM College hosts Bizz Stratathon"},
    {"month": 3, "year": 2026, "publication": "Gujarat Samachar", "date": "2026-03-15", "headline": "SU partners with India Accelerator"},
]

PRESS_RELEASE_DATA = [
    {"month": 1, "year": 2025, "title": "SU Launches New Academic Programs for 2025-26", "placements": 3, "reach": "250K"},
    {"month": 2, "year": 2025, "title": "SU Carnival 2025 Media Release", "placements": 5, "reach": "500K"},
    {"month": 3, "year": 2025, "title": "SU Faculty Recognition & Awards Announcement", "placements": 2, "reach": "180K"},
    {"month": 1, "year": 2026, "title": "SU 4th Convocation Ceremony Press Note", "placements": 4, "reach": "350K"},
    {"month": 2, "year": 2026, "title": "SU Carnival 2026 & SUMUN 2.0 Coverage", "placements": 6, "reach": "750K"},
    {"month": 3, "year": 2026, "title": "SU Signs MoU with India Accelerator", "placements": 3, "reach": "300K"},
]

class Command(BaseCommand):
    help = 'Seed demo data from January-March 2026 reports'

    def handle(self, *args, **options):
        # Create default superuser if none exists
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username='suanalytics').exists():
            User.objects.create_superuser(username='suanalytics', email='admin@su-analytics.in', password='admin')
            self.stdout.write(self.style.SUCCESS("Superuser 'suanalytics' created with password 'admin'"))

        # ── Seed all 8 colleges (idempotent) ──────────────────────
        valid_codes = {c["code"] for c in COLLEGES}
        created_colleges = []
        for c in COLLEGES:
            _, created = College.objects.get_or_create(code=c["code"], defaults={"name": c["name"]})
            created_colleges.append(created)
        # Remove any colleges that are no longer in the list (e.g. old placeholder "SU")
        stale = College.objects.exclude(code__in=valid_codes)
        stale_count = stale.count()
        stale.delete()
        self.stdout.write(f"Colleges: {sum(created_colleges)} created, {len(COLLEGES) - sum(created_colleges)} already exist, {stale_count} removed")

        college = College.objects.get(code="SCET")

        # ── University + hierarchy (#4) ─────────────────────────────
        university, _ = University.objects.get_or_create(
            code='SU',
            defaults={'name': 'Sarvajanik University', 'short_name': 'SU'},
        )
        College.objects.exclude(university=university).update(university=university)

        DEPARTMENTS = [
            {"name": "Computer Engineering", "code": "CE"},
            {"name": "Mechanical Engineering", "code": "ME"},
            {"name": "Civil Engineering", "code": "CL"},
            {"name": "Information Technology", "code": "IT"},
        ]
        departments = {}
        for d in DEPARTMENTS:
            obj, _ = Department.objects.get_or_create(
                college=college, name=d["name"], defaults={"code": d["code"]})
            departments[d["name"]] = obj

        PROGRAMMES = [
            ("Computer Engineering", "B.Tech Computer Engineering", "BTCE"),
            ("Computer Engineering", "M.Tech Computer Engineering", "MTCE"),
        ]
        programmes = {}
        for dept_name, prog_name, prog_code in PROGRAMMES:
            p, _ = Programme.objects.get_or_create(
                department=departments[dept_name], name=prog_name,
                defaults={"code": prog_code})
            programmes[prog_name] = p
        self.stdout.write(
            f"University '{university}' linked; {len(departments)} departments, "
            f"{len(programmes)} programmes seeded for SCET")

        # ── Institute-level analytics for ALL 8 colleges ───────────
        # Deterministic multipliers keep the demo realistic (SCET is the
        # largest institute) while staying reproducible across reseeds.
        MULTIPLIERS = {
            "SCET": 1.00, "SRKI": 0.60, "SRLIM": 0.45, "SCCCA": 0.35,
            "BRCM": 0.30, "SCOPA": 0.22, "SCL": 0.18, "SCLA": 0.15,
        }
        MARCH_STATUS_CYCLE = ['submitted', 'pending', 'incomplete']
        colleges_by_code = {c.code: c for c in College.objects.filter(code__in=MULTIPLIERS)}
        for idx, (code, mult) in enumerate(MULTIPLIERS.items()):
            c_obj = colleges_by_code[code]
            for a in ANALYTICS_DATA:
                if a["year"] <= 2025:
                    status = 'verified'
                else:
                    status = {1: 'verified', 2: 'submitted'}.get(
                        a['month'], MARCH_STATUS_CYCLE[idx % len(MARCH_STATUS_CYCLE)])
                MonthlyAnalytics.objects.update_or_create(
                    college=c_obj, month=a["month"], year=a["year"],
                    defaults={
                        "instagram_views": int(a["ig_views"] * mult),
                        "facebook_views": int(a["fb_views"] * mult),
                        "total_views": int((a["ig_views"] + a["fb_views"]) * mult),
                        "instagram_reach": int(a["ig_reach"] * mult),
                        "facebook_reach": int(a["fb_reach"] * mult),
                        "total_reach": int((a["ig_reach"] + a["fb_reach"]) * mult),
                        "instagram_followers": int(a["ig_followers"] * mult) + 40,
                        "youtube_subscribers": int(a["yt_subs"] * mult),
                        "followers_gained": max(1, int(a["gained"] * mult)),
                        "reels_count": int(a["reels"] * mult),
                        "graphics_count": int(a["graphics"] * mult),
                        "status": status,
                    }
                )

        # ── Department & programme breakdowns for SCET (#4) ────────
        # Stored as separate scope buckets (dept/prog FKs set) so they never
        # inflate institute-level totals — the drill-down pages read them.
        DEPT_SPLITS = [
            ("Computer Engineering", 0.55),
            ("Mechanical Engineering", 0.25),
            ("Civil Engineering", 0.20),
        ]
        # Programme rows sit under Computer Engineering (fractions of the dept)
        PROG_SPLITS = [("B.Tech Computer Engineering", 0.70),
                       ("M.Tech Computer Engineering", 0.30)]
        ce_dept = departments["Computer Engineering"]
        for a in ANALYTICS_DATA:
            dept_status = 'verified' if a["year"] <= 2025 else (
                'submitted' if a["month"] < 3 else 'pending')
            for dept_name, share in DEPT_SPLITS:
                d_obj = departments[dept_name]
                ig, fb = int(a["ig_views"] * share), int(a["fb_views"] * share)
                ig_r, fb_r = int(a["ig_reach"] * share), int(a["fb_reach"] * share)
                MonthlyAnalytics.objects.update_or_create(
                    college=college, department=d_obj, programme=None,
                    month=a["month"], year=a["year"],
                    defaults={
                        "instagram_views": ig, "facebook_views": fb,
                        "total_views": ig + fb,
                        "instagram_reach": ig_r, "facebook_reach": fb_r,
                        "total_reach": ig_r + fb_r,
                        "instagram_followers": max(1, int(a["ig_followers"] * share)),
                        "youtube_subscribers": int(a["yt_subs"] * share),
                        "followers_gained": max(1, int(a["gained"] * share)),
                        "reels_count": int(a["reels"] * share),
                        "graphics_count": int(a["graphics"] * share),
                        "status": dept_status,
                    }
                )
            for prog_name, share in PROG_SPLITS:
                p_obj = programmes[prog_name]
                ig, fb = int(a["ig_views"] * 0.55 * share), int(a["fb_views"] * 0.55 * share)
                ig_r, fb_r = int(a["ig_reach"] * 0.55 * share), int(a["fb_reach"] * 0.55 * share)
                MonthlyAnalytics.objects.update_or_create(
                    college=college, department=ce_dept, programme=p_obj,
                    month=a["month"], year=a["year"],
                    defaults={
                        "instagram_views": ig, "facebook_views": fb,
                        "total_views": ig + fb,
                        "instagram_reach": ig_r, "facebook_reach": fb_r,
                        "total_reach": ig_r + fb_r,
                        "instagram_followers": max(1, int(a["ig_followers"] * 0.55 * share)),
                        "youtube_subscribers": int(a["yt_subs"] * 0.55 * share),
                        "followers_gained": max(1, int(a["gained"] * 0.55 * share)),
                        "reels_count": int(a["reels"] * 0.55 * share),
                        "graphics_count": int(a["graphics"] * 0.55 * share),
                        "status": dept_status,
                    }
                )

        # ── KPI targets for the roll-up (#1) ───────────────────────
        TARGETS_2026 = [
            ("SCET", None, 'total_views', 1_400_000),
            ("SCET", None, 'total_reach', 160_000),
            ("SRLIM", None, 'total_views', 350_000),
            ("SRKI", None, 'total_views', 450_000),
            ("SCET", "Computer Engineering", 'total_views', 800_000),
        ]
        for code, dept_name, metric, value in TARGETS_2026:
            KpiTarget.objects.update_or_create(
                college=colleges_by_code[code],
                department=departments.get(dept_name) if dept_name else None,
                programme=None, year=2026, metric=metric,
                defaults={'target_value': value},
            )
        self.stdout.write(f"{len(TARGETS_2026)} KPI targets seeded for 2026")

        for ev in EVENTS:
            Event.objects.get_or_create(
                college=college,
                title=ev["title"],
                date=f"2026-{ev['month']:02d}-{ev['day']:02d}",
                defaults={"category": ev["category"]}
            )

        for ev in EVENTS_2025:
            Event.objects.get_or_create(
                college=college,
                title=ev["title"],
                date=f"2025-{ev['month']:02d}-{ev['day']:02d}",
                defaults={"category": ev["category"]}
            )

        # Scoped to SCET: once other institutes carry their own data, a global
        # wipe here would destroy it on every reseed.
        TopPost.objects.filter(college=college).delete()
        for year, posts_data in [(2026, TOP_POSTS), (2025, TOP_POSTS_2025)]:
            for month_num, posts in posts_data.items():
                for platform_key in ["instagram", "facebook"]:
                    for p in posts.get(platform_key, []):
                        TopPost.objects.create(
                            college=college, month=month_num, year=year,
                            platform=platform_key, views=p["views"],
                            likes=p["likes"], shares=p.get("shares", 0),
                        )

        NewspaperCoverage.objects.filter(college=college).delete()
        for n in NEWSPAPER_DATA:
            NewspaperCoverage.objects.create(
                college=college,
                month=n["month"],
                year=n["year"],
                publication=n["publication"],
                date=n["date"],
                headline=n["headline"],
            )

        PressRelease.objects.filter(college=college).delete()
        for p in PRESS_RELEASE_DATA:
            PressRelease.objects.create(
                college=college,
                month=p["month"],
                year=p["year"],
                title=p["title"],
                content=p["title"],
                date_submitted=date(p["year"], p["month"], 15),
                placements=p["placements"],
                potential_reach=p["reach"],
            )

        self.stdout.write(self.style.SUCCESS(
            f"Seed data loaded: {len(COLLEGES)} colleges, "
            f"{len(departments)} departments, {len(programmes)} programmes, "
            f"{len(ANALYTICS_DATA)} months x {len(MULTIPLIERS)} institutes, "
            f"{len(EVENTS) + len(EVENTS_2025)} events, "
            f"{sum(len(v['instagram'])+len(v['facebook']) for v in TOP_POSTS.values()) + sum(len(v['instagram'])+len(v['facebook']) for v in TOP_POSTS_2025.values())} top posts, "
            f"{len(NEWSPAPER_DATA)} newspaper clippings, "
            f"{len(PRESS_RELEASE_DATA)} press releases"
        ))
