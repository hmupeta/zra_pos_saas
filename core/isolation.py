"""Row-level tenant/branch isolation helpers."""
from rest_framework.exceptions import PermissionDenied

ADMIN_ROLES = ("SUPER_ADMIN", "TENANT_OWNER", "ADMIN")


def _context(request):
    tenant = getattr(request, "tenant", None)
    branch = getattr(request, "branch", None)
    accessible = getattr(request, "accessible_branches", None)

    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        if tenant is None:
            tenant = getattr(user, "tenant", None)
            request.tenant = tenant
        if accessible is None:
            from core.models import BranchAccess
            accessible = [a.company for a in BranchAccess.objects.filter(user=user).select_related("company")]
            request.accessible_branches = accessible
        if branch is None and tenant:
            from core.models import Company
            branch_id = request.META.get("HTTP_X_BRANCH_ID")
            if branch_id:
                branch = Company.objects.filter(id=branch_id, tenant=tenant).first()
            if branch is None and accessible:
                branch = accessible[0]
            request.branch = branch
    return tenant, branch, accessible or []


def branch_filter(request, queryset, branch_field="company"):
    tenant, branch, accessible = _context(request)
    if not tenant:
        raise PermissionDenied("No tenant context.")
    if not branch:
        raise PermissionDenied("No branch context. Select a branch first.")

    qs = queryset.filter(**{f"{branch_field}__tenant": tenant})  # always tenant-scoped
    user = request.user
    if user.is_superuser or user.user_type in ADMIN_ROLES:
        return qs
    if user.user_type == "MANAGER":
        branch_ids = [b.id for b in accessible] or [branch.id]
        return qs.filter(**{f"{branch_field}__in": branch_ids})
    return qs.filter(**{branch_field: branch})


def assert_access(request, obj, branch_field="company"):
    tenant, branch, accessible = _context(request)
    if not tenant:
        raise PermissionDenied("No tenant context.")
    obj_branch = getattr(obj, branch_field, None)
    if not obj_branch:
        return
    if obj_branch.tenant_id != tenant.id:
        raise PermissionDenied("Cross-tenant access denied")
    user = request.user
    if user.is_superuser or user.user_type in ADMIN_ROLES:
        return
    if obj_branch not in accessible:
        raise PermissionDenied("No access to this branch")