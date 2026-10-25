import os
from datetime import timedelta
from decimal import Decimal

from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from accounts.models import (
    Booking,
    Equipment,
    Facility,
    MembershipType,
    Notification,
    SportsCentre,
    User,
)

# All prices, quantities and capacities below are DEMO values, not real ones.
FACILITIES = [
    ("Football pitch", Facility.FacilityType.FIELD, 22, Decimal("15000.00"), Decimal("50000.00")),
    ("Basketball court", Facility.FacilityType.COURT, 10, Decimal("8000.00"), Decimal("0.00")),
    ("Volleyball court", Facility.FacilityType.COURT, 12, Decimal("8000.00"), Decimal("0.00")),
    ("Tennis court", Facility.FacilityType.COURT, 4, Decimal("6000.00"), Decimal("0.00")),
    ("Multipurpose hall", Facility.FacilityType.ROOM, 200, Decimal("20000.00"), Decimal("75000.00")),
]

PLANS = [
    ("Annual", 365, Decimal("20000.00"), Decimal("30000.00"), Decimal("50000.00")),
    ("Semester", 120, Decimal("12000.00"), Decimal("18000.00"), Decimal("30000.00")),
]

EQUIPMENT = [
    ("Football", "Balls", 10, Decimal("5000.00")),
    ("Basketball", "Balls", 8, Decimal("5000.00")),
    ("Tennis racket", "Rackets", 6, Decimal("4000.00")),
    ("Training bibs", "Apparel", 20, Decimal("1000.00")),
]

DEMO_USERS = [
    ("demo_member", "Demo", "Member", User.Category.STUDENT, User.Role.MEMBER),
    ("demo_coach", "Demo", "Coach", User.Category.STAFF, User.Role.COACH),
    ("demo_manager", "Demo", "Manager", User.Category.STAFF, User.Role.MANAGER),
    ("demo_finance", "Demo", "Finance", User.Category.STAFF, User.Role.FINANCE),
]


class Command(BaseCommand):
    help = "Create demo data. Safe to run more than once."

    def get(self, model, lookup, defaults, label):
        obj, created = model.objects.get_or_create(**lookup, defaults=defaults)
        if created:
            self.created += 1
            self.stdout.write(f"  created   {label}")
        else:
            self.existing += 1
            self.stdout.write(f"  existing  {label}")
        return obj

    def handle(self, *args, **options):
        self.created = 0
        self.existing = 0

        with transaction.atomic():
            centre = self.get(
                SportsCentre,
                {"name": "Centre for Sport Unit"},
                {"location": "University campus", "description": "Demo centre"},
                "sports centre",
            )

            facilities = {}
            for name, ftype, capacity, rate, event_fee in FACILITIES:
                facilities[name] = self.get(
                    Facility,
                    {"sports_centre": centre, "name": name},
                    {
                        "facility_type": ftype,
                        "capacity": capacity,
                        "hourly_rate": rate,
                        "event_fee": event_fee,
                        "availability_status": Facility.Availability.AVAILABLE,
                        "description": "Demo facility",
                    },
                    f"facility: {name}",
                )

            for name, days, student, staff, external in PLANS:
                self.get(
                    MembershipType,
                    {"name": name},
                    {
                        "description": f"{name} membership (demo)",
                        "price": student,
                        "student_price": student,
                        "staff_price": staff,
                        "external_price": external,
                        "duration_days": days,
                        "access_level": "basic",
                    },
                    f"plan: {name}",
                )

            for name, category, quantity, deposit in EQUIPMENT:
                self.get(
                    Equipment,
                    {"name": name},
                    {"category": category, "quantity": quantity, "deposit_amount": deposit},
                    f"equipment: {name}",
                )

            password = os.environ.get("SEED_DEMO_PASSWORD", "")
            if not password:
                self.stdout.write(
                    self.style.WARNING(
                        "SEED_DEMO_PASSWORD is not set: demo users were skipped."
                    )
                )
            else:
                for username, first, last, category, role in DEMO_USERS:
                    if User.objects.filter(username=username).exists():
                        self.existing += 1
                        self.stdout.write(f"  existing  user: {username}")
                        continue
                    User.objects.create_user(
                        username=username,
                        email=f"{username}@example.com",
                        password=password,
                        first_name=first,
                        last_name=last,
                        category=category,
                        role=role,
                        status=User.Status.ACTIVE,
                    )
                    self.created += 1
                    self.stdout.write(f"  created   user: {username}")

            member = User.objects.filter(username="demo_member").first()
            manager = User.objects.filter(username="demo_manager").first()
            if member and not Booking.objects.filter(user=member).exists():
                base = timezone.now().replace(
                    hour=16, minute=0, second=0, microsecond=0
                ) + timedelta(days=1)
                for facility, offset, hours, status, approver in [
                    (facilities["Football pitch"], 0, 1, Booking.Status.PENDING, None),
                    (facilities["Basketball court"], 1, 2, Booking.Status.APPROVED, manager),
                ]:
                    start = base + timedelta(days=offset)
                    Booking.objects.create(
                        user=member,
                        facility=facility,
                        start_time=start,
                        end_time=start + timedelta(hours=hours),
                        total_cost=facility.hourly_rate * hours,
                        status=status,
                        approved_by=approver,
                    )
                    self.created += 1
                    self.stdout.write(f"  created   booking: {facility.name}")

            if member:
                for title, message, ntype in [
                    ("Welcome to ALABATT-HUB", "Your account is ready.", "general"),
                    ("Booking approved", "Your basketball court booking was approved.", "booking"),
                    ("Membership reminder", "Choose a plan to activate your membership.", "membership"),
                ]:
                    self.get(
                        Notification,
                        {"user": member, "title": title},
                        {"message": message, "notification_type": ntype},
                        f"notification: {title}",
                    )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done: {self.created} created, {self.existing} already existed."
            )
        )