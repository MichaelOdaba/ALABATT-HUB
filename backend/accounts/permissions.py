from rest_framework import permissions

from .models import User


class IsAuthenticatedUser(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)


class IsManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.MANAGER
        )


class IsFinanceOfficer(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user and request.user.is_authenticated and request.user.role == User.Role.FINANCE
        )


class IsFinance(IsFinanceOfficer):
    pass


class IsManagerOrFinance(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {User.Role.MANAGER, User.Role.FINANCE}
        )


class IsManagerOrFinanceReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        if request.user.role == User.Role.MANAGER:
            return True
        return (
            request.user.role == User.Role.FINANCE
            and request.method in permissions.SAFE_METHODS
        )


class IsMemberOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role in {User.Role.MEMBER, User.Role.MANAGER}
        )


class IsMemberCoachOrManager(permissions.BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.role
            in {User.Role.MEMBER, User.Role.COACH, User.Role.MANAGER}
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False

        if request.user.role in {User.Role.MANAGER, User.Role.FINANCE}:
            return True

        return getattr(obj, 'user', None) == request.user
