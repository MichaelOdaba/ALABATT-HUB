import hashlib
import hmac
import json
from decimal import Decimal
from unittest.mock import Mock, patch

from django.test import TestCase, override_settings
from django.utils import timezone
from django.db import IntegrityError, transaction
from rest_framework.test import APIClient

from accounts.models import (
    AuditLog,
    Booking,
    Equipment,
    EquipmentLoan,
    Facility,
    Membership,
    MembershipType,
    Payment,
    SportsCentre,
    User,
)
from .services import complete_payment, mark_payment_failed


@override_settings(
    PAYSTACK_SECRET_KEY='sk_test_for_tests',
    PAYSTACK_BASE_URL='https://api.paystack.test',
)
class PaystackPaymentTests(TestCase):
    def setUp(self):
        self.client = APIClient()
        self.user = User.objects.create_user(
            username='payer',
            email='payer@example.com',
            password='SecurePass123!',
            category=User.Category.STUDENT,
        )
        self.plan = MembershipType.objects.create(
            name='Student plan',
            price=Decimal('10.00'),
            student_price=Decimal('12.34'),
        )
        self.membership = Membership.objects.create(
            user=self.user,
            membership_type=self.plan,
            start_date=timezone.localdate(),
            status=Membership.Status.PENDING,
        )
        centre = SportsCentre.objects.create(name='Main Centre', location='Campus')
        self.facility = Facility.objects.create(
            sports_centre=centre,
            name='Main Court',
            hourly_rate=Decimal('20.00'),
            event_fee=Decimal('5.00'),
        )
        self.booking = Booking.objects.create(
            user=self.user,
            facility=self.facility,
            start_time='2026-10-20T10:00:00Z',
            end_time='2026-10-20T11:30:00Z',
            is_event=True,
        )
        self.equipment = Equipment.objects.create(
            name='Tennis racket',
            category='racket',
            deposit_amount=Decimal('7.50'),
        )
        self.loan = EquipmentLoan.objects.create(
            user=self.user,
            equipment=self.equipment,
            quantity=2,
        )
        self.client.force_authenticate(user=self.user)

    @staticmethod
    def paystack_response(payload):
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = payload
        return response

    @patch('payments.services.requests.post')
    def test_membership_initiation_uses_category_price_and_returns_checkout_url(self, post):
        post.return_value = self.paystack_response(
            {'status': True, 'data': {'authorization_url': 'https://paystack.test/checkout'}}
        )

        response = self.client.post(
            '/api/payments/initiate/',
            {
                'target_type': 'membership',
                'target_id': self.membership.id,
                'amount': '0.01',
            },
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.get()
        self.assertEqual(payment.amount, Decimal('12.34'))
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)
        self.assertEqual(response.json()['authorization_url'], 'https://paystack.test/checkout')
        self.assertEqual(post.call_args.kwargs['json']['amount'], 1234)
        self.assertEqual(post.call_args.kwargs['json']['reference'], payment.reference)
        self.membership.refresh_from_db()
        self.assertEqual(self.membership.status, Membership.Status.PENDING)

    @override_settings(PAYMENT_SIMULATION=True, PAYSTACK_SECRET_KEY='')
    @patch('payments.services.requests.post')
    def test_simulation_initiates_without_calling_paystack(self, post):
        response = self.client.post(
            '/api/payments/initiate/',
            {'target_type': 'membership', 'target_id': self.membership.id},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.get()
        self.assertEqual(
            response.json()['authorization_url'],
            f'https://api.paystack.test/simulation/checkout/{payment.reference}',
        )
        post.assert_not_called()

    @override_settings(PAYMENT_SIMULATION=True, PAYSTACK_SECRET_KEY='')
    @patch('payments.services.requests.get')
    def test_simulation_verification_completes_payment_without_calling_paystack(self, get):
        payment = Payment.objects.create(
            user=self.user,
            membership=self.membership,
            amount=Decimal('12.34'),
        )

        response = self.client.get(f'/api/payments/verify/{payment.reference}/')

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.membership.refresh_from_db()
        self.assertEqual(payment.status, Payment.PaymentStatus.PAID)
        self.assertEqual(self.membership.status, Membership.Status.ACTIVE)
        get.assert_not_called()

    @patch('payments.services.requests.post')
    def test_booking_initiation_includes_server_calculated_event_fee(self, post):
        post.return_value = self.paystack_response(
            {'status': True, 'data': {'authorization_url': 'https://paystack.test/checkout'}}
        )

        response = self.client.post(
            '/api/payments/initiate/',
            {'target_type': 'booking', 'target_id': self.booking.id},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.get()
        self.booking.refresh_from_db()
        self.assertEqual(payment.amount, Decimal('35.00'))
        self.assertEqual(self.booking.total_cost, Decimal('35.00'))
        self.assertEqual(post.call_args.kwargs['json']['amount'], 3500)

    @patch('payments.services.requests.post')
    def test_pending_equipment_loan_can_start_deposit_payment(self, post):
        self.loan.status = EquipmentLoan.Status.PENDING
        self.loan.save(update_fields=['status'])
        post.return_value = self.paystack_response(
            {'status': True, 'data': {'authorization_url': 'https://paystack.test/checkout'}}
        )

        response = self.client.post(
            '/api/payments/initiate/',
            {'target_type': 'equipment_loan', 'target_id': self.loan.id},
            format='json',
        )

        self.assertEqual(response.status_code, 201)
        payment = Payment.objects.get()
        self.assertEqual(payment.amount, Decimal('15.00'))
        self.assertEqual(payment.equipment_loan, self.loan)
        self.assertEqual(post.call_args.kwargs['json']['amount'], 1500)

    @patch('payments.services.requests.get')
    def test_successful_verification_activates_membership_and_records_receipt(self, get):
        payment = Payment.objects.create(
            user=self.user,
            membership=self.membership,
            amount=Decimal('12.34'),
        )
        get.return_value = self.paystack_response(
            {
                'status': True,
                'data': {
                    'reference': payment.reference,
                    'amount': 1234,
                    'status': 'success',
                },
            }
        )

        response = self.client.get(f'/api/payments/verify/{payment.reference}/')

        self.assertEqual(response.status_code, 200)
        payment.refresh_from_db()
        self.membership.refresh_from_db()
        self.assertEqual(payment.status, Payment.PaymentStatus.PAID)
        self.assertRegex(payment.receipt_number, r'^RCP-\d{8}-\d{6}$')
        self.assertEqual(self.membership.status, Membership.Status.ACTIVE)
        self.assertEqual(self.membership.payment_status, Membership.PaymentStatus.PAID)
        self.assertTrue(
            AuditLog.objects.filter(action='membership_approved').exists()
        )

    def test_webhook_is_signed_and_idempotent(self):
        payment = Payment.objects.create(
            user=self.user,
            booking=self.booking,
            amount=Decimal('35.00'),
        )
        payload = {
            'event': 'charge.success',
            'data': {
                'reference': payment.reference,
                'amount': 3500,
                'status': 'success',
            },
        }
        raw_body = json.dumps(payload).encode('utf-8')
        signature = hmac.new(
            b'sk_test_for_tests', raw_body, hashlib.sha512
        ).hexdigest()

        first_response = self.client.post(
            '/api/payments/webhook/paystack/',
            data=raw_body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )
        second_response = self.client.post(
            '/api/payments/webhook/paystack/',
            data=raw_body,
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE=signature,
        )

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(first_response.json()['status'], 'processed')
        self.assertEqual(second_response.status_code, 200)
        self.assertEqual(second_response.json()['status'], 'already_processed')
        self.assertEqual(
            AuditLog.objects.filter(action='payment_confirmed').count(), 1
        )

    def test_successful_equipment_deposit_payment_updates_loan(self):
        self.loan.status = EquipmentLoan.Status.PENDING
        self.loan.save(update_fields=['status'])
        payment = Payment.objects.create(
            user=self.user,
            equipment_loan=self.loan,
            amount=Decimal('15.00'),
        )

        complete_payment(
            payment.reference,
            {
                'reference': payment.reference,
                'amount': 1500,
                'status': 'success',
            },
        )

        self.loan.refresh_from_db()
        self.assertEqual(self.loan.status, EquipmentLoan.Status.ACTIVE)
        self.assertEqual(self.loan.deposit_status, EquipmentLoan.DepositStatus.PAID)

    def test_failed_deposit_payment_cancels_loan_and_releases_reserved_stock(self):
        self.equipment.quantity = 2
        self.equipment.available_quantity = 0
        self.equipment.save(update_fields=['quantity', 'available_quantity'])
        self.loan.status = EquipmentLoan.Status.PENDING
        self.loan.save(update_fields=['status'])
        payment = Payment.objects.create(
            user=self.user,
            equipment_loan=self.loan,
            amount=Decimal('15.00'),
        )

        mark_payment_failed(payment)

        self.equipment.refresh_from_db()
        self.loan.refresh_from_db()
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.PaymentStatus.FAILED)
        self.assertEqual(self.loan.status, EquipmentLoan.Status.CANCELLED)
        self.assertEqual(self.equipment.available_quantity, 2)

    def test_invalid_webhook_signature_does_not_update_payment(self):
        payment = Payment.objects.create(
            user=self.user,
            booking=self.booking,
            amount=Decimal('35.00'),
        )

        response = self.client.post(
            '/api/payments/webhook/paystack/',
            data=json.dumps({'event': 'charge.success'}),
            content_type='application/json',
            HTTP_X_PAYSTACK_SIGNATURE='invalid',
        )

        self.assertEqual(response.status_code, 401)
        payment.refresh_from_db()
        self.assertEqual(payment.status, Payment.PaymentStatus.PENDING)

    def test_payment_must_have_exactly_one_target(self):
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Payment.objects.create(user=self.user, amount=Decimal('1.00'))

    def test_finance_can_read_all_payments_but_cannot_initiate_or_approve_refunds(self):
        payment = Payment.objects.create(
            user=self.user,
            membership=self.membership,
            amount=Decimal('12.34'),
        )
        from accounts.models import Refund

        refund = Refund.objects.create(
            payment=payment,
            user=self.user,
            reason='Test refund',
            amount=Decimal('5.00'),
        )
        finance = User.objects.create_user(
            username='finance',
            email='finance@example.com',
            password='SecurePass123!',
            role=User.Role.FINANCE,
        )
        self.client.force_authenticate(user=finance)

        payments_response = self.client.get('/api/payments/')
        initiate_response = self.client.post(
            '/api/payments/initiate/',
            {'target_type': 'membership', 'target_id': self.membership.id},
            format='json',
        )
        refund_response = self.client.patch(
            f'/api/refunds/{refund.id}/',
            {'status': Refund.Status.APPROVED},
            format='json',
        )

        self.assertEqual(payments_response.status_code, 200)
        self.assertEqual(len(payments_response.json()), 1)
        self.assertEqual(initiate_response.status_code, 403)
        self.assertEqual(refund_response.status_code, 403)

    def test_member_cannot_read_another_members_payment(self):
        payment = Payment.objects.create(
            user=self.user,
            membership=self.membership,
            amount=Decimal('12.34'),
        )
        other = User.objects.create_user(
            username='other',
            email='other@example.com',
            password='SecurePass123!',
        )
        self.client.force_authenticate(user=other)

        response = self.client.get(f'/api/payments/{payment.id}/')

        self.assertEqual(response.status_code, 404)
