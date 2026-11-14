import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Forcefully rebuild the shifts_list view
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

new_list_view = '''
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shifts_list(request):
    """List all shifts for this branch, recalculating math dynamically."""
    qs = Shift.objects.filter(tenant=request.tenant, company=request.branch).prefetch_related('invoices').order_by("-opening_time")
    
    data = []
    for s in qs[:100]:
        # Recalculate everything to fix historical data
        invoices = s.invoices.filter(status="PAID")
        cash_sales = sum(inv.total for inv in invoices if inv.payment_method == "CASH")
        
        expected_cash = s.opening_balance + cash_sales
        saved_actual = getattr(s, 'actual_cash', 0) or 0
        recalculated_variance = saved_actual - expected_cash
        
        data.append({
            "id": s.id,
            "cashier": s.cashier.username,
            "opening_time": s.opening_time.strftime("%Y-%m-%d %H:%M"),
            "closing_time": s.closing_time.strftime("%H:%M") if s.closing_time else "OPEN",
            "opening_balance": float(s.opening_balance),
            "expected_cash": float(expected_cash),
            "actual_cash": float(saved_actual),
            "variance": float(recalculated_variance),
            "is_closed": s.is_closed
        })
    return Response(data)
'''

# Replace the existing shifts_list function
pattern = r"@api_view\(\[\"GET\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef shifts_list\(request\):.*?return Response\(\[.*?\]\)"

if re.search(pattern, v_content, flags=re.DOTALL):
    v_content = re.sub(pattern, new_list_view.strip(), v_content, flags=re.DOTALL)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Fixed shifts_list to dynamically recalculate math.")
else:
    print("⚠️ Could not find the shifts_list function. Attempting to manually insert.")
    # Fallback: Find the start of shifts_list and replace to the next @api_view
    start_idx = v_content.find("def shifts_list(")
    if start_idx != -1:
        next_view_idx = v_content.find("@api_view", start_idx)
        if next_view_idx == -1:
            next_view_idx = len(v_content)
        
        v_content = v_content[:start_idx] + new_list_view.strip().split("def shifts_list(")[1]
        v_content = "def shifts_list(" + v_content
        views_path.write_text(v_content, encoding="utf-8")
        print("✅ Fixed using fallback method.")
    else:
        print("❌ Could not find shifts_list. Please check sales/views.py manually.")

print("\n🎉 Done! Restart the server and refresh the Shift History page.")