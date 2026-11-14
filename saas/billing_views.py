from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import Tenant
from .permissions import IsPlatformAdmin

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def admin_dashboard(request):
    return Response({
        "kpis": {
            "mrr": 1500,
            "arr": 18000,
            "active_tenants": Tenant.objects.filter(subscription_status="ACTIVE").count(),
            "trial_tenants": Tenant.objects.filter(subscription_status="TRIAL").count(),
            "pending_applications": 0,
            "upcoming_renewals_30d": 0,
            "outstanding_balance": 0,
        },
        "recent_signups": [],
        "recent_payments": []
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def admin_tenants(request):
    tenants = Tenant.objects.all()
    return Response([{
        "id": t.id,
        "code": t.code,
        "name": t.name,
        "contact_email": t.contact_email,
        "plan": t.plan.name if t.plan else None,
        "monthly_price": float(t.plan.monthly_price_zmw) if t.plan else 0,
        "subscription_status": t.subscription_status,
        "is_active": t.is_active,
        "branches_count": t.branches.count(),
        "users_count": t.users.count(),
    } for t in tenants])