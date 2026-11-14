from rest_framework.permissions import BasePermission

class IsPlatformAdmin(BasePermission):
    """Only allows users with user_type = PLATFORM_ADMIN."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "user_type", None) == "PLATFORM_ADMIN"
        )