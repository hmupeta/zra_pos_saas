from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django.shortcuts import render

# Create your views here.


class TenantEntitlementsView(APIView):
    """Returns current tenant's plan limits + live usage.
    Frontend uses this to hide/disable 'Add Branch' / 'Invite User' buttons."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plan = getattr(request, "tenant_plan", None)
        usage = getattr(request, "tenant_usage", None)
        if not plan or not usage:
            return Response({"detail": "No subscription found"}, status=404)
        return Response({
            "plan_name": plan.name,
            "features": {
                "has_pos": plan.has("has_pos"),
                "has_inventory": plan.has("has_inventory"),
                "has_zra_smart_invoice": plan.has("has_zra_smart_invoice"),
                "has_full_accounting": plan.has("has_full_accounting"),
                "has_multi_branch_reports": plan.has("has_multi_branch_reports"),
                "has_api_access": plan.has("has_api_access"),
                "has_dedicated_manager": plan.has("has_dedicated_manager"),
                "has_custom_sla": plan.has("has_custom_sla"),
            },
            "limits": {"max_branches": plan.max_branches, "max_users": plan.max_users},
            "usage": {"current_branches": usage.current_branches, "current_users": usage.current_users},
            "can_add_branch": plan.max_branches == -1 or usage.current_branches < plan.max_branches,
            "can_add_user": plan.max_users == -1 or usage.current_users < plan.max_users,
        })
