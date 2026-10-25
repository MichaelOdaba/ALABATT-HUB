from rest_framework import generics, permissions, status
from rest_framework.response import Response

from accounts.audit import record_audit_log
from accounts.models import Booking, Facility, SportsCentre
from accounts.permissions import IsManager, IsMemberCoachOrManager
from .serializers import BookingSerializer, FacilitySerializer, SportsCentreSerializer


class SportsCentreListCreateView(generics.ListCreateAPIView):
    queryset = SportsCentre.objects.all()
    serializer_class = SportsCentreSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]


class SportsCentreDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = SportsCentre.objects.all()
    serializer_class = SportsCentreSerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]


class FacilityListCreateView(generics.ListCreateAPIView):
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]


class FacilityDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Facility.objects.all()
    serializer_class = FacilitySerializer

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]


class BookingListCreateView(generics.ListCreateAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsMemberCoachOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == 'manager':
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class BookingDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsMemberCoachOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == 'manager':
            return queryset
        return queryset.filter(user=self.request.user)


class BookingDecisionView(generics.GenericAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [permissions.IsAuthenticated, IsManager]

    def post(self, request, *args, **kwargs):
        booking = self.get_object()
        decision = request.data.get('status')

        if booking.status != Booking.Status.PENDING:
            return Response(
                {'detail': 'Only pending bookings can be approved or rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )
        if decision not in {Booking.Status.APPROVED, Booking.Status.REJECTED}:
            return Response(
                {'detail': 'Status must be either approved or rejected.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = decision
        booking.approved_by = request.user if decision == Booking.Status.APPROVED else None
        booking.save(update_fields=['status', 'approved_by', 'updated_at'])
        record_audit_log(
            user=request.user,
            action=f'booking_{decision}',
            entity='booking',
            entity_id=booking.pk,
        )
        return Response(self.get_serializer(booking).data, status=status.HTTP_200_OK)


class BookingCancelView(generics.GenericAPIView):
    queryset = Booking.objects.all()
    serializer_class = BookingSerializer
    permission_classes = [IsMemberCoachOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == 'manager':
            return queryset
        return queryset.filter(user=self.request.user)

    def post(self, request, *args, **kwargs):
        booking = self.get_object()
        if booking.status != Booking.Status.PENDING:
            return Response(
                {'detail': 'Only pending bookings can be cancelled.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        booking.status = Booking.Status.CANCELLED
        booking.save(update_fields=['status', 'updated_at'])
        record_audit_log(
            user=request.user,
            action='booking_cancelled',
            entity='booking',
            entity_id=booking.pk,
        )
        return Response(self.get_serializer(booking).data, status=status.HTTP_200_OK)
