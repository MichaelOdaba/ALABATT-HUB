from rest_framework import generics, permissions

from accounts.audit import record_audit_log
from accounts.models import Membership, MembershipType, User
from accounts.permissions import IsManager, IsMemberCoachOrManager
from .serializers import MembershipSerializer, MembershipTypeSerializer


class MembershipTypeListCreateView(generics.ListCreateAPIView):
    queryset = MembershipType.objects.all()
    serializer_class = MembershipTypeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role != User.Role.MANAGER:
            return queryset.filter(is_active=True)
        return queryset

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]


class MembershipTypeDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MembershipType.objects.all()
    serializer_class = MembershipTypeSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role != User.Role.MANAGER:
            return queryset.filter(is_active=True)
        return queryset

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]


class MembershipListCreateView(generics.ListCreateAPIView):
    queryset = Membership.objects.all()
    serializer_class = MembershipSerializer
    permission_classes = [IsMemberCoachOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.MANAGER:
            return queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        membership = serializer.save(
            user=self.request.user,
            status=Membership.Status.PENDING,
            payment_status=Membership.PaymentStatus.UNPAID,
        )
        record_audit_log(
            user=self.request.user,
            action='membership_created',
            entity='membership',
            entity_id=membership.pk,
        )


class MembershipDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Membership.objects.all()
    serializer_class = MembershipSerializer
    permission_classes = [IsMemberCoachOrManager]

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.MANAGER:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]

