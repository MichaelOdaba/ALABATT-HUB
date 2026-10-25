from decimal import Decimal
import hashlib
import hmac

import requests
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from accounts.audit import record_audit_log
from accounts.models import (
    Booking,
    Equipment,
    EquipmentLoan,
    Membership,
    Payment,
)


class PaystackError(Exception):
    pass


def calculate_payment_amount(target_type, target, user):
    if target_type == 'membership':
        category_price = getattr(target.membership_type, f'{user.category}_price')
        amount = category_price if category_price is not None else target.membership_type.price
    elif target_type == 'booking':
        duration_hours = Decimal(str((target.end_time - target.start_time).total_seconds())) / Decimal('3600')
        amount = target.facility.hourly_rate * duration_hours
        if target.is_event:
            amount += target.facility.event_fee
    elif target_type == 'equipment_loan':
        amount = target.equipment.deposit_amount * target.quantity
    else:
        raise PaystackError('Unsupported payment target.')

    return amount.quantize(Decimal('0.01'))


def amount_to_kobo(amount):
    return int(amount * Decimal('100'))


def initialize_paystack_transaction(payment):
    if settings.PAYMENT_SIMULATION:
        return f'{settings.PAYSTACK_BASE_URL}/simulation/checkout/{payment.reference}'

    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError('Paystack is not configured. Set PAYSTACK_SECRET_KEY.')

    response = requests.post(
        f'{settings.PAYSTACK_BASE_URL}/transaction/initialize',
        json={
            'email': payment.user.email,
            'amount': amount_to_kobo(payment.amount),
            'currency': 'NGN',
            'reference': payment.reference,
        },
        headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    data = payload.get('data') if isinstance(payload, dict) else None
    authorization_url = data.get('authorization_url') if isinstance(data, dict) else None
    if not isinstance(payload, dict) or not payload.get('status') or not authorization_url:
        raise PaystackError('Paystack did not return an authorization URL.')
    return authorization_url


def verify_paystack_transaction(reference):
    if settings.PAYMENT_SIMULATION:
        payment = Payment.objects.get(reference=reference)
        return {
            'reference': payment.reference,
            'amount': amount_to_kobo(payment.amount),
            'status': 'success',
        }

    if not settings.PAYSTACK_SECRET_KEY:
        raise PaystackError('Paystack is not configured. Set PAYSTACK_SECRET_KEY.')

    response = requests.get(
        f'{settings.PAYSTACK_BASE_URL}/transaction/verify/{reference}',
        headers={'Authorization': f'Bearer {settings.PAYSTACK_SECRET_KEY}'},
        timeout=20,
    )
    response.raise_for_status()
    payload = response.json()
    if (
        not isinstance(payload, dict)
        or not payload.get('status')
        or not isinstance(payload.get('data'), dict)
    ):
        raise PaystackError('Paystack could not verify this transaction.')
    return payload['data']


def validate_paystack_transaction(payment, transaction_data):
    if transaction_data.get('reference') != payment.reference:
        raise PaystackError('Paystack reference does not match this payment.')
    try:
        provider_amount = int(transaction_data['amount'])
    except (KeyError, TypeError, ValueError) as exc:
        raise PaystackError('Paystack transaction amount is missing or invalid.') from exc
    if provider_amount != amount_to_kobo(payment.amount):
        raise PaystackError('Paystack transaction amount does not match this payment.')


def complete_payment(reference, transaction_data):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(reference=reference)
        validate_paystack_transaction(payment, transaction_data)

        if payment.status == Payment.PaymentStatus.PAID:
            return payment, False
        if payment.status != Payment.PaymentStatus.PENDING:
            raise PaystackError('This payment is no longer pending.')
        if transaction_data.get('status') != 'success':
            raise PaystackError('Paystack has not marked this transaction successful.')

        now = timezone.now()
        payment.status = Payment.PaymentStatus.PAID
        payment.paid_at = now
        payment.receipt_number = f'RCP-{now:%Y%m%d}-{payment.pk:06d}'
        payment.save(update_fields=['status', 'paid_at', 'receipt_number', 'updated_at'])

        if payment.membership_id:
            membership = payment.membership
            membership.status = Membership.Status.ACTIVE
            membership.payment_status = Membership.PaymentStatus.PAID
            membership.save(update_fields=['status', 'payment_status', 'updated_at'])
            record_audit_log(
                user=payment.user,
                action='membership_approved',
                entity='membership',
                entity_id=membership.pk,
            )
        elif payment.equipment_loan_id:
            loan = payment.equipment_loan
            loan.deposit_status = EquipmentLoan.DepositStatus.PAID
            if loan.status == EquipmentLoan.Status.PENDING:
                loan.status = EquipmentLoan.Status.ACTIVE
            loan.save(update_fields=['deposit_status', 'status'])

        record_audit_log(
            user=payment.user,
            action='payment_confirmed',
            entity='payment',
            entity_id=payment.pk,
        )
        return payment, True


def mark_payment_failed(payment):
    with transaction.atomic():
        payment = Payment.objects.select_for_update().get(pk=payment.pk)
        if payment.status != Payment.PaymentStatus.PENDING:
            return
        payment.status = Payment.PaymentStatus.FAILED
        payment.save(update_fields=['status', 'updated_at'])

        if payment.equipment_loan_id:
            loan = EquipmentLoan.objects.select_for_update().get(
                pk=payment.equipment_loan_id
            )
            if loan.status == EquipmentLoan.Status.PENDING:
                equipment = Equipment.objects.select_for_update().get(
                    pk=loan.equipment_id
                )
                equipment.available_quantity += loan.quantity
                equipment.save(update_fields=['available_quantity'])
                loan.status = EquipmentLoan.Status.CANCELLED
                loan.save(update_fields=['status'])


def is_valid_paystack_signature(raw_body, signature):
    if not settings.PAYSTACK_SECRET_KEY or not signature:
        return False
    expected_signature = hmac.new(
        settings.PAYSTACK_SECRET_KEY.encode('utf-8'),
        raw_body,
        hashlib.sha512,
    ).hexdigest()
    return hmac.compare_digest(expected_signature, signature)
