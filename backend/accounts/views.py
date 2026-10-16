from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken

from .audit import record_audit_log
from .models import AuditLog, User
from .permissions import IsManagerOrFinance
from .serializers import AuditLogSerializer, RegisterSerializer, UserSerializer


class AuditLogListView(generics.ListAPIView):
    queryset = AuditLog.objects.select_related('user').all()
    serializer_class = AuditLogSerializer
    permission_classes = [IsManagerOrFinance]


class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = [permissions.AllowAny]
    serializer_class = RegisterSerializer


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username') or request.data.get('email')
        password = request.data.get('password')

        if not username or not password:
            return Response(
                {'detail': 'Username/email and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        user = None
        if '@' in username:
            user = User.objects.filter(email__iexact=username).first()
        else:
            user = User.objects.filter(username__iexact=username).first()

        if user is None or not user.check_password(password):
            return Response({'detail': 'Invalid credentials.'}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(user)

        return Response(
            {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': UserSerializer(user).data,
            },
            status=status.HTTP_200_OK,
        )


class CurrentUserView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        serializer = UserSerializer(request.user)
        return Response(serializer.data, status=status.HTTP_200_OK)


class PromoteUserRoleView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        actor = request.user
        if not (actor.is_staff or actor.is_superuser or actor.role == User.Role.MANAGER):
            return Response(
                {'detail': 'Only staff or managers may update user roles.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        user_id = request.data.get('user_id')
        requested_role = request.data.get('role')

        if user_id is None or requested_role is None:
            return Response(
                {'detail': 'user_id and role are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if requested_role not in User.Role.values:
            return Response(
                {'detail': 'Invalid role value.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if requested_role in {User.Role.MANAGER, User.Role.FINANCE} and not (actor.is_staff or actor.is_superuser):
            return Response(
                {'detail': 'Only staff members can assign manager or finance roles.'},
                status=status.HTTP_403_FORBIDDEN,
            )

        user = get_object_or_404(User, pk=user_id)
        previous_role = user.role
        user.role = requested_role
        if requested_role in {User.Role.MANAGER, User.Role.FINANCE, User.Role.COACH}:
            user.is_staff = True
        user.save(update_fields=['role', 'is_staff'])

        if previous_role != user.role:
            record_audit_log(
                user=actor,
                action='role_changed',
                entity='user',
                entity_id=user.pk,
            )

        return Response(UserSerializer(user).data, status=status.HTTP_200_OK)
