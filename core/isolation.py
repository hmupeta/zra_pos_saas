"""Row-level tenant/branch isolation helpers."""
from rest_framework.exceptions import PermissionDenied


def branch_filter(request, queryset, branch_field="company"):
    if not request.branch:
        raise PermissionDenied("No branch context. Select a branch first.")

    user = request.user
    if user.user_type in ("SUPER_ADMIN", "TENANT_OWNER", "ADMIN"):
        return queryset.filter(**{f"{branch_field}__tenant": request.tenant})
    if user.user_type == "MANAGER":
        branch_ids = [b.id for b in request.accessible_branches]
        return queryset.filter(**{f"{branch_field}__in": branch_ids})
    return queryset.filter(**{branch_field: request.branch})


def assert_access(request, obj, branch_field="company"):
    obj_branch = getattr(obj, branch_field, None)
    if not obj_branch:
        return
    if obj_branch.tenant_id != request.tenant.id:
        raise PermissionDenied("Cross-tenant access denied")
    if (obj_branch not in request.accessible_branches
            and request.user.user_type not in ("SUPER_ADMIN", "TENANT_OWNER", "ADMIN")):
        raise PermissionDenied("No access to this branch")
