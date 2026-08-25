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


class Command(BaseCommand):
    help = 'Seed structural data (colleges + university). No analytics/events are fabricated.'

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

        # ── University hierarchy ────────────────────────────────────
        university, _ = University.objects.get_or_create(
            code='SU',
            defaults={'name': 'Sarvajanik University', 'short_name': 'SU'},
        )
        College.objects.exclude(university=university).update(university=university)
        self.stdout.write(f"University '{university}' linked to all colleges")

        # ── SCET departments + programmes (structure only) ─────────
        college = College.objects.get(code="SCET")
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
        programmes_count = 0
        for dept_name, prog_name, prog_code in PROGRAMMES:
            _, created = Programme.objects.get_or_create(
                department=departments[dept_name], name=prog_name,
                defaults={"code": prog_code})
            programmes_count += int(created)
        self.stdout.write(
            f"SCET structure: {len(DEPARTMENTS)} departments, "
            f"{programmes_count} new programmes")

        # All analytics/event/report figures are entered by users via the
        # app forms or admin panel — nothing numeric is pre-populated.

        self.stdout.write(self.style.SUCCESS(
            f"Seed complete: {len(COLLEGES)} colleges linked under '{university}'."
        ))
