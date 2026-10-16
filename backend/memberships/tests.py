from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from accounts.models import AuditLog, Membership, MembershipType, User


class MembershipWorkflowTests(TestCase):
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
        self.plan = MembershipType.objects.create(
            name='Monthly', price='25.00', duration_days=30
        )
        self.client.force_authenticate(user=self.member)

    def test_member_application_uses_pending_unpaid_state_and_calculated_end_date(self):
        start_date = timezone.localdate() + timedelta(days=1)
        response = self.client.post(
            '/api/memberships/',
            {
                'user': self.other_member.id,
                'membership_type': self.plan.id,
                'start_date': start_date.isoformat(),
                'end_date': '2099-01-01',
                'status': Membership.Status.ACTIVE,
                'payment_status': Membership.PaymentStatus.PAID,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        membership = Membership.objects.get()
        self.assertEqual(membership.user, self.member)
        self.assertEqual(membership.status, Membership.Status.PENDING)
        self.assertEqual(membership.payment_status, Membership.PaymentStatus.UNPAID)
        self.assertEqual(membership.end_date, start_date + timedelta(days=30))
        self.assertEqual(AuditLog.objects.get().action, 'membership_created')

    def test_member_only_sees_their_own_memberships(self):
        own_membership = Membership.objects.create(
            user=self.member,
            membership_type=self.plan,
            start_date=timezone.localdate(),
        )
        Membership.objects.create(
            user=self.other_member,
            membership_type=self.plan,
            start_date=timezone.localdate(),
        )

        response = self.client.get('/api/memberships/')

        self.assertEqual(response.status_code, 200)
        self.assertEqual([item['id'] for item in response.json()], [own_membership.id])

    def test_member_cannot_approve_membership(self):
        membership = Membership.objects.create(
            user=self.member,
            membership_type=self.plan,
            start_date=timezone.localdate(),
        )

        response = self.client.patch(
            f'/api/memberships/{membership.id}/',
            {'status': Membership.Status.ACTIVE},
            format='json',
        )

        self.assertEqual(response.status_code, 403)
        membership.refresh_from_db()
        self.assertEqual(membership.status, Membership.Status.ACTIVE)

    def test_manager_cannot_activate_membership_before_payment_succeeds(self):
        membership = Membership.objects.create(
            user=self.member,
            membership_type=self.plan,
            start_date=timezone.localdate(),
            status=Membership.Status.PENDING,
        )
        self.client.force_authenticate(user=self.manager)

        response = self.client.patch(
            f'/api/memberships/{membership.id}/',
            {
                'status': Membership.Status.ACTIVE,
                'payment_status': Membership.PaymentStatus.PAID,
            },
            format='json',
        )

        self.assertEqual(response.status_code, 400)
        membership.refresh_from_db()
        self.assertEqual(membership.status, Membership.Status.PENDING)
        self.assertEqual(membership.payment_status, Membership.PaymentStatus.UNPAID)
        self.assertFalse(AuditLog.objects.exists())