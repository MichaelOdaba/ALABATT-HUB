import os
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from accounts.models import (
    Booking, Equipment, Facility, MembershipType, Notification, SportsCentre, User,
)

MODELS = (SportsCentre, Facility, MembershipType, Equipment, User, Booking, Notification)


def counts():
    return tuple(m.objects.count() for m in MODELS)


def run_seed(password):
    with patch.dict(os.environ, {"SEED_DEMO_PASSWORD": password}):
        call_command("seed_demo", stdout=StringIO())


class SeedDemoTests(TestCase):
    def test_running_twice_creates_no_duplicates(self):
        run_seed("Demo-pass-123")
        first = counts()
        run_seed("Demo-pass-123")
        self.assertEqual(first, counts())
        self.assertEqual(Facility.objects.count(), 5)
        self.assertEqual(User.objects.count(), 4)

    def test_without_password_no_users_are_created(self):
        run_seed("")
        self.assertEqual(User.objects.count(), 0)
        self.assertEqual(Facility.objects.count(), 5)