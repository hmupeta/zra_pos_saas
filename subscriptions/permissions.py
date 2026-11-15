"""Phase 2A/2E - feature-flag enforcement helpers.

Rules:
  - Anonymous users pass through (so @login_required can redirect them).
  - Superusers always pass (so admins can test gated features).
  - Everyone else is checked against their tenant's plan flags.
"""
from functools import wraps
from django.http import JsonResponse
from rest_framework.permissions import BasePermission


class FeatureNotAvailable(Exception):
    """Raised when the current plan doesn't include the required feature."""
    def __init__(self, feature):
        self.feature = feature
        super().__init__(f"Plan does not include {feature}")


def user_can(request, feature: str) -> bool:
    """Return True if the current user may use the given plan feature."""
    user = getattr(request, "user", None)

    # Anonymous - let the view's own @login_required handle the redirect
    if user is None or not getattr(user, "is_authenticated", False):
        return True

    # Superusers bypass all gates (admin testing)
    if getattr(user, "is_superuser", False):
        return True

    plan = getattr(request, "tenant_plan", None)
    return bool(plan and getattr(plan, feature, False))


def requires_plan_feature(feature: str):
    """Plain-Django decorator - returns 402 Payment Required if flag is False.

    Anonymous users pass through so that @login_required (if present) can
    redirect them to login instead of showing a 402.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                if not user_can(request, feature):
                    return JsonResponse(
                        {"error": "feature_not_available", "feature": feature,
                         "message": "This feature is not included in your plan. "
                                    "Upgrade to access it."},
                        status=402,
                    )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class HasPlanFeature(BasePermission):
    """DRF permission class - reads `required_feature` from the view."""
    message = "This feature is not included in your plan."

    def has_permission(self, request, view):
        feature = getattr(view, "required_feature", None)
        if not feature:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return user_can(request, feature)
