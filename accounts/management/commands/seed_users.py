"""
Management command: seed_users
-------------------------------
Creates one demo user per role with fixed credentials.
Safe to run multiple times (idempotent).

Usage:
    python manage.py seed_users

Credentials created
-------------------
Role            | Username          | Password
----------------|-------------------|------------------
super_admin     | super_admin       | SuperAdmin@123
college_admin   | college_admin     | CollegeAdmin@123
analytics_team  | analytics_team    | Analytics@123
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from accounts.models import Profile
from colleges.models import College

User = get_user_model()

# ── Demo user definitions ────────────────────────────────────────────────────
DEMO_USERS = [
    {
        "username":   "super_admin",
        "password":   "SuperAdmin@123",
        "email":      "super_admin@su-analytics.in",
        "first_name": "Super",
        "last_name":  "Admin",
        "role":       "super_admin",
        "is_staff":   True,
        "is_superuser": True,
        "college_code": None,          # super admin sees all colleges
    },
    {
        "username":   "college_admin",
        "password":   "CollegeAdmin@123",
        "email":      "college_admin@su-analytics.in",
        "first_name": "College",
        "last_name":  "Admin",
        "role":       "college_admin",
        "is_staff":   False,
        "is_superuser": False,
        "college_code": "SCET",        # scoped to SCET by default
    },
    {
        "username":   "analytics_team",
        "password":   "Analytics@123",
        "email":      "analytics@su-analytics.in",
        "first_name": "Analytics",
        "last_name":  "Team",
        "role":       "analytics_team",
        "is_staff":   False,
        "is_superuser": False,
        "college_code": "SCET",
    },
]


class Command(BaseCommand):
    help = "Seed one demo user per role with fixed credentials (idempotent)."

    def handle(self, *args, **options):
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Seeding demo users ===\n"))

        for spec in DEMO_USERS:
            college = None
            if spec["college_code"]:
                try:
                    college = College.objects.get(code=spec["college_code"])
                except College.DoesNotExist:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  College '{spec['college_code']}' not found — "
                            f"run `python manage.py seed_data` first."
                        )
                    )

            user, created = User.objects.get_or_create(
                username=spec["username"],
                defaults={
                    "email":        spec["email"],
                    "first_name":   spec["first_name"],
                    "last_name":    spec["last_name"],
                    "is_staff":     spec["is_staff"],
                    "is_superuser": spec["is_superuser"],
                },
            )

            # Always reset password so it matches the spec
            user.set_password(spec["password"])
            user.is_staff     = spec["is_staff"]
            user.is_superuser = spec["is_superuser"]
            user.save()

            # Update (or create) the profile
            profile, _ = Profile.objects.get_or_create(user=user)
            profile.role    = spec["role"]
            profile.college = college
            profile.save()

            status = "CREATED" if created else "UPDATED"
            self.stdout.write(
                self.style.SUCCESS(
                    f"  [{status}]  username={spec['username']:<20} "
                    f"password={spec['password']:<22} "
                    f"role={spec['role']}"
                )
            )

        # ── Also fix existing superusers whose profile role is wrong ────────
        self.stdout.write(self.style.MIGRATE_HEADING("\n=== Fixing existing superuser profiles ===\n"))
        for user in User.objects.filter(is_superuser=True).exclude(username__in=[d["username"] for d in DEMO_USERS]):
            profile, _ = Profile.objects.get_or_create(user=user)
            if profile.role != "super_admin":
                profile.role = "super_admin"
                profile.save()
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  Fixed: {user.username} → role set to super_admin"
                    )
                )

        self.stdout.write(self.style.SUCCESS("\n✓ Done. Login credentials:\n"))
        self.stdout.write(
            "  Role             Username          Password\n"
            "  ─────────────────────────────────────────────────\n"
            "  super_admin      super_admin       SuperAdmin@123\n"
            "  college_admin    college_admin     CollegeAdmin@123\n"
            "  analytics_team   analytics_team    Analytics@123\n"
        )
