from django.test import TestCase
from rest_framework.test import APIClient

from .models import (
    Booking,
    Equipment,
    EquipmentLoan,
    Facility,
    Membership,
    MembershipType,
    Notification,
    Payment,
    Refund,
    SportsCentre,
    User,
)


class SportsCentreDomainModelsTests(TestCase):
    def setUp(self):
        self.client = APIClient()

    def test_auth_login_returns_token_payload(self):
        user = User.objects.create_user(
            username="member1",
            email="member1@example.com",
            password="SecurePass123!",
            first_name="Ada",
            last_name="Lovelace",
            category=User.Category.STUDENT,
            role=User.Role.MEMBER,
        )

        response = self.client.post(
            '/api/auth/login/',
            {'username': 'member1', 'password': 'SecurePass123!'},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn('access', response.json())
        self.assertIn('refresh', response.json())
        self.assertEqual(response.json()['user']['email'], user.email)

    def test_public_registration_cannot_create_manager_role(self):
        response = self.client.post(
            '/api/auth/register/',
            {
                'username': 'newmember',
                'email': 'newmember@example.com',
                'password': 'SecurePass123!',
                'first_name': 'New',
                'last_name': 'Member',
                'category': User.Category.STUDENT,
                'role': User.Role.MANAGER,
            },
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json()['role'], User.Role.MEMBER)
        self.assertNotEqual(response.json()['role'], User.Role.MANAGER)

    def test_manager_admin_can_promote_user_to_manager_role(self):
        admin = User.objects.create_user(
            username="adminuser",
            email="adminuser@example.com",
            password="SecurePass123!",
            first_name="Admin",
            last_name="User",
            category=User.Category.STAFF,
            role=User.Role.MANAGER,
            is_staff=True,
            is_superuser=True,
        )
        member = User.objects.create_user(
            username="member2",
            email="member2@example.com",
            password="SecurePass123!",
            first_name="Member",
            last_name="Two",
            category=User.Category.STUDENT,
            role=User.Role.MEMBER,
        )

        self.client.force_authenticate(user=admin)
        response = self.client.post(
            '/api/auth/users/role/',
            {'user_id': member.id, 'role': User.Role.MANAGER},
            content_type='application/json',
        )

        self.assertEqual(response.status_code, 200)
        member.refresh_from_db()
        self.assertEqual(member.role, User.Role.MANAGER)
        self.assertTrue(member.is_staff)

    def test_core_domain_models_can_be_created(self):
        user = User.objects.create_user(
            username="member1",
            email="member1@example.com",
            password="SecurePass123!",
            first_name="Ada",
            last_name="Lovelace",
            category=User.Category.STUDENT,
            role=User.Role.MEMBER,
        )

        centre = SportsCentre.objects.create(
            name="City Sports Centre",
            location="Main Road",
            contact_phone="123456789",
            email="info@example.com",
        )

        membership_type = MembershipType.objects.create(
            name="Student Premium",
            price=25.00,
            duration_days=30,
        )

        membership = Membership.objects.create(
            user=user,
            membership_type=membership_type,
            start_date="2026-01-01",
            end_date="2026-01-31",
            status=Membership.Status.ACTIVE,
            payment_status=Membership.PaymentStatus.PAID,
        )

        facility = Facility.objects.create(
            sports_centre=centre,
            name="Swimming Pool",
            facility_type=Facility.FacilityType.POOL,
            hourly_rate=15.00,
            capacity=10,
        )

        booking = Booking.objects.create(
            user=user,
            facility=facility,
            start_time="2026-01-10T09:00:00Z",
            end_time="2026-01-10T10:00:00Z",
            total_cost=15.00,
            status=Booking.Status.APPROVED,
        )

        equipment = Equipment.objects.create(
            name="Tennis Racket",
            category="sport",
            quantity=2,
            deposit_amount=20.00,
        )

        equipment_loan = EquipmentLoan.objects.create(
            user=user,
            equipment=equipment,
            quantity=1,
            due_date="2026-01-15T12:00:00Z",
            status=EquipmentLoan.Status.ACTIVE,
        )

        payment = Payment.objects.create(
            user=user,
            booking=booking,
            membership=membership,
            amount=15.00,
            payment_method=Payment.PaymentMethod.CARD,
            status=Payment.PaymentStatus.PAID,
            receipt_number="RCPT-001",
        )

        refund = Refund.objects.create(
            payment=payment,
            user=user,
            reason="Booking cancelled",
            amount=15.00,
            status=Refund.Status.PENDING,
        )

        notification = Notification.objects.create(
            user=user,
            title="Membership active",
            message="Your membership is active.",
            notification_type="membership",
        )

        self.assertEqual(str(user), "Ada Lovelace")
        self.assertEqual(str(centre), "City Sports Centre")
        self.assertEqual(str(membership_type), "Student Premium")
        self.assertEqual(str(facility), "City Sports Centre - Swimming Pool")
        self.assertEqual(str(booking), f"{user} - {facility} (2026-01-10T09:00:00Z)")
        self.assertEqual(str(equipment), "Tennis Racket")
        self.assertEqual(str(payment), f"{user} - 15.00")
        self.assertEqual(refund.payment, payment)
        self.assertEqual(notification.user, user)
        self.assertTrue(membership.pk)
