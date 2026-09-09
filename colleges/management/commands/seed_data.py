from datetime import date
from django.core.management.base import BaseCommand
from colleges.models import College, Department, Programme, University

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

# Dummy analytics per college: (month, instagram_views, facebook_views, instagram_reach,
#   facebook_reach, instagram_followers, facebook_followers, youtube_subscribers,
#   followers_gained, reels_count, graphics_count)
ANALYTICS_TEMPLATE = [
    (1,  45000, 12000, 38000, 9000,  520, 210, 80,  180, 12, 18),
    (2,  52000, 14500, 42000, 11000, 610, 240, 95,  220, 15, 22),
    (3,  61000, 16000, 50000, 13000, 720, 270, 110, 260, 18, 25),
    (4,  48000, 11000, 39000, 8500,  490, 200, 75,  160, 10, 16),
    (5,  55000, 13000, 44000, 10000, 580, 230, 90,  200, 14, 20),
    (6,  38000,  9000, 30000,  7000, 420, 180, 65,  140,  8, 14),
]

# Dummy events per college: (title, category, month, day, description)
EVENTS_TEMPLATE = [
    ("Annual Tech Fest",          "workshop",       2, 15, "Annual technology festival with competitions and exhibitions."),
    ("Industry Expert Guest Talk","guest_lecture",  3, 10, "Guest lecture by industry professionals on emerging trends."),
    ("Cultural Fest",             "cultural",       4,  5, "Inter-college cultural festival with performances and art."),
    ("Placement Drive",           "placement",      5, 20, "Campus placement drive with top recruiters."),
    ("Sports Day",                "sports",         6, 12, "Annual sports day with track and field events."),
    ("Academic Conference",       "conference",     1, 25, "National-level academic conference on research innovations."),
]


class Command(BaseCommand):
    help = 'Seed structural data (colleges + university) with dummy analytics & events.'

    def handle(self, *args, **options):
        year = date.today().year

        # ── Superuser ─────────────────────────────────────────────────
        from django.contrib.auth import get_user_model
        User = get_user_model()
        if not User.objects.filter(username='suanalytics').exists():
            User.objects.create_superuser(
                username='suanalytics', email='admin@su-analytics.in', password='admin')
            self.stdout.write(self.style.SUCCESS("Superuser 'suanalytics' created"))

        # ── University ────────────────────────────────────────────────
        university, _ = University.objects.get_or_create(
            code='SU',
            defaults={'name': 'Sarvajanik University', 'short_name': 'SU'},
        )

        # ── Colleges ──────────────────────────────────────────────────
        valid_codes = {c["code"] for c in COLLEGES}
        created_count = 0
        for c in COLLEGES:
            _, created = College.objects.get_or_create(
                code=c["code"], defaults={"name": c["name"], "university": university})
            if created:
                created_count += 1
        stale = College.objects.exclude(code__in=valid_codes)
        stale_count = stale.count()
        stale.delete()
        College.objects.exclude(university=university).update(university=university)
        self.stdout.write(
            f"Colleges: {created_count} created, "
            f"{len(COLLEGES) - created_count} already exist, "
            f"{stale_count} removed — all linked to '{university}'"
        )

        # ── SCET departments + programmes ─────────────────────────────
        scet = College.objects.get(code="SCET")
        DEPARTMENTS = [
            {"name": "Computer Engineering",  "code": "CE"},
            {"name": "Mechanical Engineering","code": "ME"},
            {"name": "Civil Engineering",     "code": "CL"},
            {"name": "Information Technology","code": "IT"},
        ]
        departments = {}
        for d in DEPARTMENTS:
            obj, _ = Department.objects.get_or_create(
                college=scet, name=d["name"], defaults={"code": d["code"]})
            departments[d["name"]] = obj

        PROGRAMMES = [
            ("Computer Engineering", "B.Tech Computer Engineering", "BTCE"),
            ("Computer Engineering", "M.Tech Computer Engineering", "MTCE"),
        ]
        prog_count = 0
        for dept_name, prog_name, prog_code in PROGRAMMES:
            _, created = Programme.objects.get_or_create(
                department=departments[dept_name], name=prog_name,
                defaults={"code": prog_code})
            prog_count += int(created)
        self.stdout.write(f"SCET: {len(DEPARTMENTS)} departments, {prog_count} new programmes")

        # ── Dummy analytics (idempotent via get_or_create) ────────────
        from analytics_app.models import MonthlyAnalytics
        analytics_created = 0
        for college in College.objects.all():
            for (month, ig_v, fb_v, ig_r, fb_r, ig_f, fb_f, yt_s, fg, rc, gc) in ANALYTICS_TEMPLATE:
                _, created = MonthlyAnalytics.objects.get_or_create(
                    college=college, month=month, year=year,
                    department=None, programme=None,
                    defaults=dict(
                        instagram_views=ig_v, facebook_views=fb_v,
                        instagram_reach=ig_r, facebook_reach=fb_r,
                        instagram_followers=ig_f, facebook_followers=fb_f,
                        youtube_subscribers=yt_s, followers_gained=fg,
                        reels_count=rc, graphics_count=gc,
                        status='verified',
                    )
                )
                if created:
                    analytics_created += 1
        self.stdout.write(f"Analytics: {analytics_created} new entries seeded")

        # ── Dummy events (idempotent via get_or_create) ───────────────
        from events.models import Event
        events_created = 0
        for college in College.objects.all():
            for (title, category, month, day, desc) in EVENTS_TEMPLATE:
                event_date = date(year, month, day)
                _, created = Event.objects.get_or_create(
                    college=college, title=title, date=event_date,
                    defaults=dict(
                        category=category,
                        description=desc,
                        approval_status=Event.ApprovalStatus.CONFIRMED,
                    )
                )
                if created:
                    events_created += 1
        self.stdout.write(f"Events: {events_created} new entries seeded")

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {len(COLLEGES)} colleges under '{university}'."))
