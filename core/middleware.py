from django.http import JsonResponse
from rest_framework.authtoken.models import Token
from core.models import BranchAccess, Company

ADMIN_ROLES = ("SUPER_ADMIN", "TENANT_OWNER", "ADMIN", "PLATFORM_ADMIN")


def resolve_user(request):
    """Session user if present, otherwise resolve the DRF token early."""
    if request.user.is_authenticated:
        return request.user
    auth = request.META.get("HTTP_AUTHORIZATION", "")
    if auth.startswith("Token "):
        key = auth.split(" ", 1)[1].strip()
        try:
            return Token.objects.select_related("user").get(key=key).user
        except Token.DoesNotExist:
            return None
    return None


class TenantBranchMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.tenant = None
        request.branch = None
        request.accessible_branches = []

        user = resolve_user(request)
        if user is None:
            return self.get_response(request)

        tenant = getattr(user, "tenant", None)
        request.tenant = tenant
        if not tenant:
            return self.get_response(request)

        # Owners/admins: all tenant branches. Others: their BranchAccess rows.
        if user.is_superuser or user.user_type in ADMIN_ROLES:
            request.accessible_branches = list(Company.objects.filter(tenant=tenant))
        else:
            request.accessible_branches = [
                a.company for a in BranchAccess.objects.filter(
                    user=user, company__tenant=tenant
                ).select_related("company")
            ]

        # Header branch must be tenant-valid AND accessible to this user.
        branch = None
        branch_id = request.META.get("HTTP_X_BRANCH_ID")
        if branch_id:
            candidate = Company.objects.filter(id=branch_id, tenant=tenant).first()
            if candidate and candidate in request.accessible_branches:
                branch = candidate
        if branch is None and request.accessible_branches:
            branch = request.accessible_branches[0]
        request.branch = branch

        return self.get_response(request)