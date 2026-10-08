from rest_framework.permissions import BasePermission
from .models import Profile


def role(user):
    if not user.is_authenticated:
        return None
    if user.is_superuser:
        return Profile.Role.ADMIN
    try:
        return user.profile.role
    except Profile.DoesNotExist:
        return Profile.Role.CUSTOMER


def is_admin(user):
    return role(user) == Profile.Role.ADMIN


def is_manager(user):
    return role(user) in (Profile.Role.ADMIN, Profile.Role.MANAGER)


def can_see_internal_notes(user):
    """Internal notes are staff-only: managers and admins. Customers and technicians never see them."""
    return is_manager(user)


class WorkOrderAccess(BasePermission):
    def has_object_permission(self, request, view, obj):
        r = role(request.user)
        if r == Profile.Role.ADMIN:
            return True
        if obj.status == obj.Status.CLOSED and request.method not in ("GET", "HEAD", "OPTIONS"):
            return False
        if r == Profile.Role.MANAGER:
            return True
        if r == Profile.Role.TECHNICIAN:
            return obj.technician_id == request.user.id
        if obj.customer_id != request.user.id:
            return False
        # Customers are read-only, except they may add comments/attachments to their own open requests.
        read_only = request.method in ("GET", "HEAD", "OPTIONS")
        return read_only or getattr(view, "action", None) in ("comments", "attachments")


class IsManagerOrAdmin(BasePermission):
    message = "Restricted to managers and admins."

    def has_permission(self, request, view):
        return request.user.is_authenticated and is_manager(request.user)
