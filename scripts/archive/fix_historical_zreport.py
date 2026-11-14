import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Forcefully rebuild the shift_details view to recalculate math on the fly
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

new_details_view = '''
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shift_details(request, pk):
    """Get details of a specific shift, including all its sales."""
    try:
        shift = Shift.objects.get(pk=pk, tenant=request.tenant)
    except Shift.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
        
    invoices = shift.invoices.filter(status="PAID")
    
    # --- RECALCULATE EVERYTHING ON THE FLY TO FIX HISTORICAL DATA ---
    total_sales = sum(inv.total for inv in invoices)
    cash_sales = sum(inv.total for inv in invoices if inv.payment_method == "CASH")
    momo_sales = sum(inv.total for inv in invoices if inv.payment_method in ("MOMO", "MTN", "AIRTEL", "ZAMTEL"))
    card_sales = sum(inv.total for inv in invoices if inv.payment_method == "CARD")
    
    # Recalculate expected cash (Opening Float + Cash Sales)
    expected_cash = shift.opening_balance + cash_sales
    
    # Use saved actual_cash if it exists, else default to 0
    saved_actual = getattr(shift, 'actual_cash', 0) or 0
    
    # Recalculate variance based on recalculated expected cash
    recalculated_variance = saved_actual - expected_cash
    
    return Response({
        "shift": {
            "id": shift.id,
            "cashier": shift.cashier.username,
            "opening_time": shift.opening_time.strftime("%Y-%m-%d %H:%M"),
            "closing_time": shift.closing_time.strftime("%Y-%m-%d %H:%M") if shift.closing_time else None,
            "opening_balance": float(shift.opening_balance),
            "expected_cash": float(expected_cash), 
            "actual_cash": float(saved_actual),
            "variance": float(recalculated_variance),
            "total_sales": float(total_sales),
            "cash_sales": float(cash_sales),
            "momo_sales": float(momo_sales),
            "card_sales": float(card_sales),
        },
        "sales": [{
            "invoice_number": i.invoice_number,
            "time": i.created_at.strftime("%H:%M"),
            "customer": i.customer_name,
            "total": float(i.total),
            "payment_method": i.payment_method
        } for i in invoices]
    })
'''

# Regex to replace the entire shift_details function
pattern = r"@api_view\(\[\"GET\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef shift_details\(request, pk\):.*?return Response\(\{\n        \"shift\": \{.*?\"sales\": \[.*?\]\n    \}\)"

if re.search(pattern, v_content, flags=re.DOTALL):
    v_content = re.sub(pattern, new_details_view.strip(), v_content, flags=re.DOTALL)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Backend now recalculates historical shift data on the fly.")
else:
    print("⚠️ Regex failed. Trying a broader replacement...")
    # Fallback: Find the start of shift_details and replace to the end of the file or next view
    start_idx = v_content.find("def shift_details(")
    if start_idx != -1:
        # Find the end of this function (look for next '@api_view' or end of file)
        next_view_idx = v_content.find("@api_view", start_idx)
        if next_view_idx == -1:
            next_view_idx = len(v_content)
        
        v_content = v_content[:start_idx] + new_details_view.strip().split("def shift_details(")[1]
        v_content = "def shift_details(" + v_content
        views_path.write_text(v_content, encoding="utf-8")
        print("✅ Backend updated using fallback.")
    else:
        print("❌ Could not find shift_details function.")

# ============================================================
# 2. Ensure the UI displays these fields correctly
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "shifts.html"
h_content = html_path.read_text(encoding="utf-8")

# Check if the UI has the 3-column layout
if "Mobile Money Sales" not in h_content:
    print("⚠️ UI is missing the breakdown. Re-applying UI patch...")
    new_summary = '''
          <!-- Financial Summary -->
          <div class="grid grid-cols-3 gap-4 mb-4 bg-gray-50 p-4 rounded-lg border">
            <div>
              <div class="text-xs text-gray-500 uppercase font-bold">Total Sales</div>
              <div class="font-bold text-xl text-brand-700" x-text="formatCurrency(selectedShift.shift.total_sales)"></div>
            </div>
            <div>
              <div class="text-xs text-gray-500 uppercase font-bold">Cash Sales</div>
              <div class="font-bold text-xl text-green-700" x-text="formatCurrency(selectedShift.shift.cash_sales)"></div>
            </div>
            <div>
              <div class="text-xs text-gray-500 uppercase font-bold">Mobile Money Sales</div>
              <div class="font-bold text-xl text-yellow-600" x-text="formatCurrency(selectedShift.shift.momo_sales)"></div>
            </div>
          </div>

          <div class="grid grid-cols-4 gap-4 mb-6 bg-slate-100 p-4 rounded-lg shadow-inner">
            <div>
              <div class="text-xs text-gray-500 uppercase font-bold">Opening Float</div>
              <div class="font-medium text-slate-700" x-text="formatCurrency(selectedShift.shift.opening_balance)"></div>
            </div>
            <div>
              <div class="text-xs text-gray-500 uppercase font-bold">Expected Cash</div>
              <div class="font-bold text-lg text-slate-800" x-text="formatCurrency(selectedShift.shift.expected_cash)"></div>
            </div>
            <div>
              <div class="text-xs text-gray-500 uppercase font-bold">Actual Cash</div>
              <div class="font-bold text-lg text-slate-800" x-text="formatCurrency(selectedShift.shift.actual_cash)"></div>
            </div>
            <div>
              <div class="text-xs text-gray-500 uppercase font-bold">Variance</div>
              <div class="font-bold text-lg" :class="selectedShift.shift.variance < 0 ? 'text-red-600' : selectedShift.shift.variance > 0 ? 'text-green-600' : 'text-gray-500'" x-text="formatCurrency(selectedShift.shift.variance)"></div>
            </div>
          </div>
    '''
    pattern = r"<!-- Financial Summary -->.*?x-text=\"formatCurrency\(selectedShift\.sales\.reduce.*?</div>\s*</div>"
    h_content = re.sub(pattern, new_summary, h_content, flags=re.DOTALL)
    html_path.write_text(h_content, encoding="utf-8")
    print("✅ UI updated.")
else:
    print("✅ UI already has the breakdown layout.")

print("\n🎉 Done! Restart the server, go to Shift History, and click 'View Report'.")