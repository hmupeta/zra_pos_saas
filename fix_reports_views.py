from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "reports" / "views.py"

combined_views = '''
from datetime import timedelta
from django.db.models import Sum, Count
from django.db.models.functions import TruncDate
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from sales.models import Invoice, InvoiceItem
from inventory.models import Product
from core.isolation import branch_filter


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sales_summary(request):
    period = request.query_params.get("period", "today")
    now = timezone.now()
    start = now.replace(hour=0, minute=0, second=0) if period == "today" else now - timedelta(days=7)
    
    qs = branch_filter(request, Invoice.objects.filter(created_at__gte=start, status="PAID"))
    agg = qs.aggregate(total=Sum("total"), count=Count("id"), tax=Sum("tax_total"))
    
    return Response({
        "period": period,
        "total_sales": float(agg["total"] or 0),
        "transaction_count": agg["count"] or 0,
        "total_tax": float(agg["tax"] or 0),
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def dashboard(request):
    now = timezone.now()
    today = now.replace(hour=0, minute=0, second=0, microsecond=0)
    last_7_days = today - timedelta(days=6)
    
    # Base Querysets
    branch_invoices = branch_filter(request, Invoice.objects.all())
    today_invoices = branch_invoices.filter(created_at__gte=today, status="PAID")
    
    # 1. KPIs
    agg = today_invoices.aggregate(t=Sum("total"), c=Count("id"))
    total_products = Product.objects.filter(tenant=request.tenant, company=request.branch, is_active=True).count()
    low_stock = Product.objects.filter(tenant=request.tenant, company=request.branch, current_stock__lte=10, is_active=True).count()

    # 2. Sales Trend (Last 7 Days)
    trend_qs = branch_invoices.filter(created_at__gte=last_7_days, status="PAID") \\
        .annotate(date=TruncDate('created_at')) \\
        .values('date') \\
        .annotate(total=Sum('total')) \\
        .order_by('date')
    
    trend_labels = [item['date'].strftime('%a, %d %b') for item in trend_qs]
    trend_data = [float(item['total']) for item in trend_qs]

    # 3. Payment Methods
    pm_qs = branch_invoices.filter(status="PAID").values('payment_method').annotate(total=Sum('total'))
    pm_labels = [item['payment_method'] for item in pm_qs]
    pm_data = [float(item['total']) for item in pm_qs]

    # 4. Top Selling Products
    top_qs = InvoiceItem.objects.filter(invoice__in=branch_invoices.filter(status="PAID")) \\
        .values('product__name') \\
        .annotate(qty=Sum('quantity')) \\
        .order_by('-qty')[:5]
    
    top_labels = [item['product__name'] for item in top_qs]
    top_data = [float(item['qty']) for item in top_qs]

    return Response({
        "kpis": {
            "today_sales": float(agg["t"] or 0),
            "today_transactions": agg["c"] or 0,
            "total_products": total_products,
            "low_stock": low_stock,
        },
        "charts": {
            "trend": {"labels": trend_labels, "data": trend_data},
            "payments": {"labels": pm_labels, "data": pm_data},
            "top_products": {"labels": top_labels, "data": top_data}
        },
        "tenant": request.tenant.name if request.tenant else None,
        "branch": request.branch.name if request.branch else None,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def agent_performance(request):
    """Restricted to Managers and Owners to see how much each cashier sold."""
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Only Managers can view performance"}, status=403)
        
    # Group invoices by cashier
    perf = Invoice.objects.filter(tenant=request.tenant, status="PAID").values("cashier__username").annotate(
        total_sales=Sum("total"), 
        transaction_count=Count("id")
    ).order_by("-total_sales")
    
    return Response([{
        "agent": p["cashier__username"],
        "total_sales": float(p["total_sales"]),
        "transactions": p["transaction_count"]
    } for p in perf])
'''

views_path.write_text(combined_views.strip(), encoding="utf-8")
print("✅ Fixed reports/views.py to include both Dashboard Charts and Agent Performance.")
print("🎉 Done! Restart your server.")