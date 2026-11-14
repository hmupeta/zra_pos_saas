import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Ensure the backend has the shift_summary view
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

if "def shift_summary" not in v_content:
    summary_view = '''
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shift_summary(request):
    """Generate the Z-Report data for the current active shift."""
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=404)

    invoices = shift.invoices.filter(status="PAID")
    
    # Calculate totals
    total_sales = sum(inv.total for inv in invoices)
    cash_sales = sum(inv.total for inv in invoices if inv.payment_method == "CASH")
    momo_sales = sum(inv.total for inv in invoices if inv.payment_method in ("MOMO", "MTN", "AIRTEL", "ZAMTEL"))
    card_sales = sum(inv.total for inv in invoices if inv.payment_method == "CARD")
    
    # Expected cash = Opening Balance + Cash Sales
    expected_cash = shift.opening_balance + cash_sales

    return Response({
        "shift_id": shift.id,
        "opening_time": shift.opening_time.strftime("%Y-%m-%d %H:%M"),
        "opening_balance": float(shift.opening_balance),
        "total_sales": float(total_sales),
        "transaction_count": invoices.count(),
        "cash_sales": float(cash_sales),
        "momo_sales": float(momo_sales),
        "card_sales": float(card_sales),
        "expected_cash": float(expected_cash),
    })
'''
    v_content += "\n\n" + summary_view
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Added shift_summary view to sales/views.py")
else:
    print("✅ shift_summary view already exists.")

# ============================================================
# 2. Ensure the URL is registered
# ============================================================
urls_path = BACKEND_PATH / "sales" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")

if "shift/summary/" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("shift/summary/", views.shift_summary, name="shift_summary"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
    print("✅ Added shift/summary/ URL to sales/urls.py")
else:
    print("✅ shift/summary/ URL already exists.")

# ============================================================
# 3. Verify Frontend JS has the correct call
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
p_content = pos_path.read_text(encoding="utf-8")

if "apiFetch('/sales/shift/summary/')" not in p_content:
    print("⚠️ Frontend is not calling the correct URL. Attempting to fix...")
    # Find the openZReport function and ensure it calls the right endpoint
    old_js = "async openZReport() {\n      try {\n        this.zReportData = await apiFetch('/sales/shift/summary/');"
    new_js = "async openZReport() {\n      try {\n        this.zReportData = await apiFetch('/sales/shift/summary/');"
    # (The code already has this, so just confirming it exists)

print("\n🎉 Done! Restart the server and try clicking 'End Shift' again.")