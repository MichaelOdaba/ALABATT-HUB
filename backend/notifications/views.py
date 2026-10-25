from rest_framework import generics, permissions

from accounts.models import Notification, User
from accounts.permissions import IsManager, IsMemberCoachOrManager
from .serializers import NotificationSerializer


class NotificationListCreateView(generics.ListCreateAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.MANAGER:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        return [IsManager()]


class NotificationDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Notification.objects.all()
    serializer_class = NotificationSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.user.role == User.Role.MANAGER:
            return queryset
        return queryset.filter(user=self.request.user)

    def get_permissions(self):
        if self.request.method in permissions.SAFE_METHODS:
            return [IsMemberCoachOrManager()]
        if self.request.method == 'PATCH':
            return [IsMemberCoachOrManager()]
        return [IsManager()]
