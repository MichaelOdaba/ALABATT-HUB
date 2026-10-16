import json

import requests
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import record_audit_log
from accounts.models import (
    Booking,
    EquipmentLoan,
    Membership,
    Payment,
    Refund,
    User,
)
from accounts.permissions import IsManager, IsMemberCoachOrManager
from .serializers import PaymentInitiationSerializer, PaymentSerializer, RefundSerializer
from .services import (
    PaystackError,
    calculate_payment_amount,
    complete_payment,
    initialize_paystack_transaction,
    is_valid_paystack_signature,
    mark_payment_failed,
    verify_paystack_transaction,
)


class PaymentListView(generics.ListAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role in {User.Role.MANAGER, User.Role.FINANCE}:
            return queryset
        return queryset.filter(user=self.request.user)


class PaymentDetailView(generics.RetrieveAPIView):
    queryset = Payment.objects.all()
    serializer_class = PaymentSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role in {User.Role.MANAGER, User.Role.FINANCE}:
            return queryset
        return queryset.filter(user=self.request.user)


class PaymentInitiateView(APIView):
    permission_classes = [IsMemberCoachOrManager]

    def post(self, request, *args, **kwargs):
        if not settings.PAYSTACK_SECRET_KEY:
            return Response(
                {'detail': 'Paystack is not configured. Set PAYSTACK_SECRET_KEY.'},
                status=status.HTTP_503_SERVICE_UNAVAILABLE,
            )

        input_serializer = PaymentInitiationSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)
        target_type = input_serializer.validated_data['target_type']
        target_id = input_serializer.validated_data['target_id']
        target, relation_field = self.get_target(
            target_type, target_id, request.user
        )

        if not self.target_can_be_paid(target_type, target):
            return Response(
                {'detail': 'This item is not currently payable.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if Payment.objects.filter(
            **{relation_field: target},
            status__in=[Payment.PaymentStatus.PENDING, Payment.PaymentStatus.PAID],
        ).exists():
            return Response(
                {'detail': 'A pending or completed payment already exists for this item.'},
                status=status.HTTP_409_CONFLICT,
            )

        amount = calculate_payment_amount(target_type, target, request.user)
        if amount <= 0:
            return Response(
                {'detail': 'The calculated payment amount must be greater than zero.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if target_type == PaymentInitiationSerializer.TargetType.BOOKING:
            target.total_cost = amount
            target.save(update_fields=['total_cost', 'updated_at'])

        payment = Payment.objects.create(
            user=request.user,
            amount=amount,
            **{relation_field: target},
        )
        try:
            authorization_url = initialize_paystack_transaction(payment)
        except (requests.RequestException, PaystackError, ValueError):
            mark_payment_failed(payment)
            return Response(
                {'detail': 'Could not initialize the Paystack transaction.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                'payment': PaymentSerializer(payment).data,
                'authorization_url': authorization_url,
            },
            status=status.HTTP_201_CREATED,
        )

    @staticmethod
    def get_target(target_type, target_id, user):
        target_specs = {
            PaymentInitiationSerializer.TargetType.MEMBERSHIP: (Membership, 'membership'),
            PaymentInitiationSerializer.TargetType.BOOKING: (Booking, 'booking'),
            PaymentInitiationSerializer.TargetType.EQUIPMENT_LOAN: (EquipmentLoan, 'equipment_loan'),
        }
        model, relation_field = target_specs[target_type]
        target = get_object_or_404(model, pk=target_id, user=user)
        return target, relation_field

    @staticmethod
    def target_can_be_paid(target_type, target):
        if target_type == PaymentInitiationSerializer.TargetType.MEMBERSHIP:
            return (
                target.status == Membership.Status.PENDING
                and target.payment_status == Membership.PaymentStatus.UNPAID
            )
        if target_type == PaymentInitiationSerializer.TargetType.BOOKING:
            return target.status in {Booking.Status.PENDING, Booking.Status.APPROVED}
        return (
            target.status == EquipmentLoan.Status.PENDING
            and target.deposit_status == EquipmentLoan.DepositStatus.UNPAID
        )


class PaymentVerifyView(APIView):
    permission_classes = [IsMemberCoachOrManager]

    def get(self, request, reference, *args, **kwargs):
        payment = get_object_or_404(Payment, reference=reference, user=request.user)
        try:
            transaction_data = verify_paystack_transaction(reference)
            if transaction_data.get('status') == 'success':
                payment, _ = complete_payment(reference, transaction_data)
            elif transaction_data.get('status') == 'failed':
                mark_payment_failed(payment)
        except (requests.RequestException, PaystackError, ValueError):
            return Response(
                {'detail': 'Could not verify the Paystack transaction.'},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        return Response(PaymentSerializer(payment).data, status=status.HTTP_200_OK)


class PaystackWebhookView(APIView):
    authentication_classes = []
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        signature = request.headers.get('x-paystack-signature', '')
        if not is_valid_paystack_signature(request.body, signature):
            return Response(
                {'detail': 'Invalid Paystack signature.'},
                status=status.HTTP_401_UNAUTHORIZED,
            )

        try:
            payload = json.loads(request.body)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return Response(
                {'detail': 'Invalid JSON payload.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if not isinstance(payload, dict):
            return Response(
                {'detail': 'Expected a JSON object.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if payload.get('event') != 'charge.success':
            return Response({'status': 'ignored'}, status=status.HTTP_200_OK)

        transaction_data = payload.get('data')
        if not isinstance(transaction_data, dict):
            return Response(
                {'detail': 'Missing transaction data.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        reference = transaction_data.get('reference')
        if not reference:
            return Response(
                {'detail': 'Missing transaction reference.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            payment, processed = complete_payment(reference, transaction_data)
        except Payment.DoesNotExist:
            return Response(
                {'detail': 'Payment reference not found.'},
                status=status.HTTP_404_NOT_FOUND,
            )
        except PaystackError as exc:
            return Response({'detail': str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(
            {'status': 'processed' if processed else 'already_processed'},
            status=status.HTTP_200_OK,
        )


class RefundListCreateView(generics.ListCreateAPIView):
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role in {User.Role.MANAGER, User.Role.FINANCE}:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsManager()]


class RefundDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Refund.objects.all()
    serializer_class = RefundSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role in {User.Role.MANAGER, User.Role.FINANCE}:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [permissions.IsAuthenticated()]
        return [IsManager()]

    def perform_update(self, serializer):
        previous_status = serializer.instance.status
        refund = serializer.save()
        if (
            previous_status != refund.status
            and refund.status in {Refund.Status.APPROVED, Refund.Status.REJECTED}
        ):
            record_audit_log(
                user=self.request.user,
                action=f'refund_{refund.status}',
                entity='refund',
                entity_id=refund.pk,
            )
