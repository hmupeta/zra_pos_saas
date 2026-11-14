from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import Customer
import uuid

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def customers_list(request):
    if request.method == "GET":
        q = request.query_params.get("search", "")
        qs = Customer.objects.filter(tenant=request.tenant).order_by("-total_spent")
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone_number__icontains=q))
            
        return Response([{
            "id": c.id, "name": c.full_name, "phone": c.phone_number,
            "loyalty_points": float(c.loyalty_points), "total_spent": float(c.total_spent),
            "credit_limit": float(c.credit_limit), "account_balance": float(c.account_balance)
        } for c in qs[:50]])
        
    # POST: Quick Create from POS
    data = request.data
    phone = data.get("phone_number")
    if Customer.objects.filter(tenant=request.tenant, phone_number=phone).exists():
        return Response({"error": "Phone number already registered"}, status=400)
        
    import uuid
    c = Customer.objects.create(
        tenant=request.tenant, company=request.branch,
        customer_id=f"CUST{uuid.uuid4().hex[:6].upper()}",
        first_name=data.get("first_name", "Walk-in"),
        last_name=data.get("last_name", ""),
        phone_number=phone,
        email=data.get("email", ""),
        credit_limit=data.get("credit_limit", 0)
    )
    return Response({"success": True, "id": c.id, "name": c.full_name})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_search_pos(request):
    """Lightweight search for the POS dropdown"""
    q = request.query_params.get("q", "")
    if not q or len(q) < 3:
        return Response([])
    qs = Customer.objects.filter(tenant=request.tenant).filter(
        Q(phone_number__icontains=q) | Q(first_name__icontains=q)
    )[:5]
    return Response([{"id": c.id, "name": c.full_name, "phone": c.phone_number, "points": float(c.loyalty_points)} for c in qs])