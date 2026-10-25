from rest_framework.permissions import BasePermission


class IsAdminRole(BasePermission):
    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.role == "admin")


class IsStaffRole(BasePermission):
    """Approved campus staff or administrators."""

    def has_permission(self, request, view):
        u = request.user
        return bool(u and u.is_authenticated and u.is_active and u.role in ("staff", "admin"))


def can_release(user):
    return bool(user.is_authenticated and user.is_active and (
        user.role == "admin" or (user.role == "staff" and user.can_release_items)))


def can_review_scope(user):
    return bool(user.is_authenticated and user.is_active and (
        user.role == "admin" or (user.role == "staff" and user.can_review_claims)))
