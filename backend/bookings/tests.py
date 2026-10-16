from decimal import Decimal

from django.test import TestCase
from rest_framework.test import APIClient

from accounts.models import AuditLog, Booking, Facility, SportsCentre, User


class BookingWorkflowTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.member = User.objects.create_user(
            username='member',
            email='member@example.com',
            password='SecurePass123!',
        )
        self.other_member = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='SecurePass123!',
        )
        self.manager = User.objects.create_user(
            username='manager',
            email='manager@example.com',
            password='SecurePass123!',
            role=User.Role.MANAGER,
        )
        centre = SportsCentre.objects.create(name='Main Centre', location='Campus')
        self.facility = Facility.objects.create(
            sports_centre=centre,
            name='Court 1',
            hourly_rate=Decimal('20.00'),
        )
        self.client.force_authenticate(user=self.member)

    def booking_payload(self, **overrides):
        payload = {
            'facility': self.facility.id,
            'start_time': '2026-10-20T10:00:00Z',
            'end_time': '2026-10-20T11:30:00Z',
        }
        payload.update(overrides)
        return payload

    def test_member_booking_uses_owner_pending_status_and_calculated_price(self):
        response = self.client.post(
            '/api/bookings/',
            self.booking_payload(
                user=self.other_member.id,
                status=Booking.Status.APPROVED,
                total_cost='0.01',
            ),
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        booking = Booking.objects.get()
        self.assertEqual(booking.user, self.member)
        self.assertEqual(booking.status, Booking.Status.PENDING)
        self.assertEqual(booking.total_cost, Decimal('30.00'))

    def test_member_only_sees_their_own_bookings(self):
        own_booking = Booking.objects.create(
            user=self.member,
            facility=self.facility,
            start_time='2026-10-20T10:00:00Z',
            end_time='2026-10-20T11:00:00Z',
        )
        Booking.objects.create(
            user=self.other_member,
            facility=self.facility,
            start_time='2026-10-20T12:00:00Z',
            end_time='2026-10-20T13:00:00Z',
        )

        response = self.client.get('/api/bookings/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()], [own_booking.id])

    def test_overlapping_booking_is_rejected(self):
        Booking.objects.create(
            user=self.other_member,
            facility=self.facility,
            start_time='2026-10-20T10:30:00Z',
            end_time='2026-10-20T11:30:00Z',
        )

        response = self.client.post(
            '/api/bookings/', self.booking_payload(), format='json'
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Booking.objects.count(), 1)

    def test_manager_can_approve_pending_booking(self):
        booking = Booking.objects.create(
            user=self.member,
            facility=self.facility,
            start_time='2026-10-20T10:00:00Z',
            end_time='2026-10-20T11:00:00Z',
        )
        self.client.force_authenticate(user=self.manager)

        response = self.client.post(
            f'/api/bookings/{booking.id}/decision/',
            {'status': Booking.Status.APPROVED},
            format='json',
        )

        self.assertEqual(response.status_code, 200)
        booking.refresh_from_db()
        self.assertEqual(booking.status, Booking.Status.APPROVED)
        self.assertEqual(booking.approved_by, self.manager)
        self.assertEqual(AuditLog.objects.get().action, 'booking_approved')

    def test_only_coaches_and_managers_can_create_event_bookings(self):
        member_response = self.client.post(
            '/api/bookings/',
            self.booking_payload(is_event=True),
            format='json',
        )
        coach = User.objects.create_user(
            username='coach',
            email='coach@example.com',
            password='SecurePass123!',
            role=User.Role.COACH,
        )
        self.client.force_authenticate(user=coach)
        coach_response = self.client.post(
            '/api/bookings/',
            self.booking_payload(is_event=True),
            format='json',
        )

        self.assertEqual(member_response.status_code, 400)
        self.assertEqual(coach_response.status_code, 201)
        self.assertTrue(Booking.objects.get().is_event)

    def test_member_cannot_change_facility_inventory(self):
        response = self.client.patch(
            f'/api/facilities/{self.facility.id}/',
            {'hourly_rate': '0.00'},
            format='json',
        )

        self.assertEqual(response.status_code, 403)