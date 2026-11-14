# core/middleware.py
from django.utils.deprecation import MiddlewareMixin
from core.models import Company
from rest_framework.authentication import TokenAuthentication
from rest_framework.exceptions import AuthenticationFailed


class TenantBranchMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.tenant = None
        request.branch = None
        request.accessible_branches = []

        user = getattr(request, "user", None)

        # --- FIX: Manually check DRF Token Auth in middleware ---
        if not user or not user.is_authenticated:
            try:
                auth = TokenAuthentication()
                user_auth_tuple = auth.authenticate(request)
                if user_auth_tuple:
                    request.user = user_auth_tuple[0]
                    request.auth = user_auth_tuple[1]
                    user = request.user
            except AuthenticationFailed:
                pass
        # --------------------------------------------------------

        if not user or not user.is_authenticated:
            return None

        request.tenant = getattr(user, "tenant", None)
        
        if not request.tenant:
            return None

        # Active branch resolution
        branch_id = request.session.get("branch_id") or request.META.get("HTTP_X_BRANCH_ID")

        qs = user.branch_access.filter(company__tenant=request.tenant, company__is_active=True).select_related("company")
        request.accessible_branches = [ba.company for ba in qs]

        if branch_id:
            branch = Company.objects.filter(pk=branch_id, tenant=request.tenant).first()
            if branch and branch in request.accessible_branches:
                request.branch = branch
        if not request.branch:
            default = qs.filter(is_default=True).first()
            request.branch = default.company if default else (
                request.accessible_branches[0] if request.accessible_branches else None
            )

        return None