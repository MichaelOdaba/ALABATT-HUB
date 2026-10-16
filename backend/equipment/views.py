from django.db import transaction
from django.utils import timezone
from rest_framework import generics, permissions, status
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.audit import record_audit_log
from accounts.models import Equipment, EquipmentLoan
from accounts.permissions import IsManager, IsMemberCoachOrManager
from .serializers import EquipmentLoanSerializer, EquipmentSerializer


class EquipmentListCreateView(generics.ListCreateAPIView):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]


class EquipmentDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Equipment.objects.all()
    serializer_class = EquipmentSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]


class EquipmentLoanListCreateView(generics.ListCreateAPIView):
    queryset = EquipmentLoan.objects.all()
    serializer_class = EquipmentLoanSerializer
    permission_classes = [IsMemberCoachOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == 'manager':
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        quantity = serializer.validated_data['quantity']
        with transaction.atomic():
            equipment = Equipment.objects.select_for_update().get(
                pk=serializer.validated_data['equipment'].pk
            )
            if quantity > equipment.available_quantity:
                raise ValidationError(
                    {'quantity': 'Requested quantity exceeds available stock.'}
                )
            equipment.available_quantity -= quantity
            equipment.save(update_fields=['available_quantity'])
            serializer.save(
                user=self.request.user,
                equipment=equipment,
                status=EquipmentLoan.Status.PENDING,
                deposit_status=EquipmentLoan.DepositStatus.UNPAID,
            )


class EquipmentLoanDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = EquipmentLoan.objects.all()
    serializer_class = EquipmentLoanSerializer
    permission_classes = [IsMemberCoachOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == 'manager':
            return queryset
        return queryset.filter(user=self.request.user)

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]

    def perform_update(self, serializer):
        serializer.save()


class EquipmentLoanReturnView(APIView):
    permission_classes = [IsManager]

    def post(self, request, pk, *args, **kwargs):
        deposit_status = request.data.get('deposit_status')
        allowed_deposit_statuses = {
            EquipmentLoan.DepositStatus.RETURNED,
            EquipmentLoan.DepositStatus.FORFEITED,
        }
        if deposit_status not in allowed_deposit_statuses:
            return Response(
                {'detail': 'deposit_status must be returned or forfeited.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            loan = EquipmentLoan.objects.select_for_update().filter(pk=pk).first()
            if loan is None:
                return Response(
                    {'detail': 'Equipment loan not found.'},
                    status=status.HTTP_404_NOT_FOUND,
                )
            if (
                loan.status != EquipmentLoan.Status.ACTIVE
                or loan.deposit_status != EquipmentLoan.DepositStatus.PAID
            ):
                return Response(
                    {'detail': 'Only active loans with a paid deposit can be returned.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            equipment = Equipment.objects.select_for_update().get(pk=loan.equipment_id)
            if equipment.available_quantity + loan.quantity > equipment.quantity:
                return Response(
                    {'detail': 'Returning this loan would exceed the equipment stock.'},
                    status=status.HTTP_409_CONFLICT,
                )
            equipment.available_quantity += loan.quantity
            equipment.save(update_fields=['available_quantity'])
            loan.status = EquipmentLoan.Status.RETURNED
            loan.return_date = timezone.now()
            loan.deposit_status = deposit_status
            loan.save(update_fields=['status', 'return_date', 'deposit_status'])
            record_audit_log(
                user=request.user,
                action='equipment_returned',
                entity='equipment_loan',
                entity_id=loan.pk,
            )

        return Response(EquipmentLoanSerializer(loan).data, status=status.HTTP_200_OK)
