"""Create demo users and sample work orders: python manage.py seed_demo"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.db import transaction
from service.models import Comment, WorkOrder, WorkOrderEvent

User = get_user_model()
PASSWORD = "Demo@12345"
USERS = [
    ("admin", "ADMIN", "Ada", "Admin"),
    ("manager1", "MANAGER", "Mia", "Manager"),
    ("tech1", "TECHNICIAN", "Tom", "Tech"),
    ("tech2", "TECHNICIAN", "Tara", "Tech"),
    ("customer1", "CUSTOMER", "Cara", "Client"),
    ("customer2", "CUSTOMER", "Carl", "Client"),
]


class Command(BaseCommand):
    help = "Create demo users (password Demo@12345) and sample work orders. Safe to re-run."

    @transaction.atomic
    def handle(self, *args, **options):
        made = {}
        for username, role, first, last in USERS:
            u, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": f"{username}@example.com",
                    "first_name": first,
                    "last_name": last,
                },
            )
            if created:
                u.set_password(PASSWORD)
            if role == "ADMIN":
                u.is_staff = u.is_superuser = True
            elif role == "MANAGER":
                u.is_staff = True
            u.save()
            u.profile.role = role
            if role == "CUSTOMER":
                u.profile.company = "Acme Ltd" if username == "customer1" else "Globex"
            u.profile.save()
            made[username] = u
        if not WorkOrder.objects.exists():
            m, t1, t2, c1, c2 = (made[k] for k in ("manager1", "tech1", "tech2", "customer1", "customer2"))

            def mk(title, cust, prio, status, tech=None):
                o = WorkOrder.objects.create(
                    title=title,
                    description=title + " - demo data",
                    customer=cust,
                    priority=prio,
                    status=status,
                    technician=tech,
                    location="Site A",
                )
                WorkOrderEvent.objects.create(
                    work_order=o,
                    actor=cust,
                    event_type="CREATED",
                    to_value="OPEN",
                )
                if tech:
                    WorkOrderEvent.objects.create(
                        work_order=o,
                        actor=m,
                        event_type="ASSIGNED",
                        to_value=str(tech.pk),
                    )
                return o
            mk("Printer not working", c1, "LOW", "OPEN")
            o = mk("Air conditioner leaking", c1, "HIGH", "ASSIGNED", t1)
            mk("Network outage in office", c2, "URGENT", "IN_PROGRESS", t2)
            mk("Replace lobby lights", c2, "NORMAL", "COMPLETED", t1)
            mk("Server room inspection", c1, "NORMAL", "CLOSED", t2)
            Comment.objects.create(
                work_order=o,
                author=m,
                body="Customer prefers morning visit.",
                is_internal=True,
            )
            Comment.objects.create(work_order=o, author=t1, body="Will visit tomorrow 9am.")
        self.stdout.write(
            self.style.SUCCESS("Demo data ready. All demo users use password: " + PASSWORD),
        )
