"""
Management command: seed three demo approval requests.

Usage:
    python manage.py seed_approvals
    python manage.py seed_approvals --email admin@demo.com --site "Skyline Towers"

The command is idempotent: it skips rows whose title already exists.
"""

from django.core.management.base import BaseCommand, CommandError

from accounts.models import User
from approvals.models import ApprovalRequest, ApprovalType


DEMO_ROWS = [
    {
        "type": ApprovalType.SITE_MANAGER_CHANGE,
        "site_name": "Skyline Towers",
        "title": "Remove backup manager",
        "details": {"managerId": None, "backupManagerId": None},
    },
    {
        "type": ApprovalType.STOCK_ADJUSTMENT,
        "site_name": "Green Valley Apartments",
        "title": "2 · Physical count shortfall",
        "details": {"qty": 2, "direction": -1, "reason": "Physical count shortfall"},
    },
    {
        "type": ApprovalType.MATERIAL_ISSUE,
        "site_name": "Green Valley Apartments",
        "title": "4 → Block A · Terrace",
        "details": {"qty": 4, "workArea": "Block A · Terrace", "notes": "Terrace waterproofing, level 2"},
    },
]


class Command(BaseCommand):
    help = "Seed three demo pending approval requests"

    def add_arguments(self, parser):
        parser.add_argument(
            "--email",
            default="",
            help="Email of the user who 'submitted' the demo requests. Defaults to the first non-superadmin.",
        )

    def handle(self, *args, **options):
        email = options["email"].strip()
        if email:
            try:
                submitter = User.objects.get(email=email)
            except User.DoesNotExist:
                raise CommandError(f"No user with email '{email}' found.")
        else:
            submitter = User.objects.filter(is_superuser=False, is_active=True).order_by("id").first()
            if not submitter:
                submitter = User.objects.order_by("id").first()
            if not submitter:
                raise CommandError("No users found. Create at least one user first.")

        created = 0
        for row in DEMO_ROWS:
            if ApprovalRequest.objects.filter(title=row["title"], type=row["type"]).exists():
                self.stdout.write(f"  skip  {row['title']}")
                continue
            ApprovalRequest.objects.create(submitted_by=submitter, **row)
            self.stdout.write(self.style.SUCCESS(f"  created  {row['title']}"))
            created += 1

        self.stdout.write(self.style.SUCCESS(f"\nDone — {created} approval(s) created, submitted as '{submitter.email}'"))
