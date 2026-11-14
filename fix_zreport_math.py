import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Fix the Backend (Save expected_amount in close_shift & return breakdown)
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Fix close_shift
old_close = '''    shift.closing_time = timezone.now()
    shift.actual_cash = actual_cash
    shift.variance = variance
    shift.is_closed = True
    shift.save()'''

new_close = '''    shift.closing_time = timezone.now()
    shift.expected_amount = expected_cash
    shift.actual_cash = actual_cash
    shift.variance = variance
    shift.is_closed = True
    shift.save()'''

if old_close in v_content:
    v_content = v_content.replace(old_close, new_close)
    print("✅ Fixed close_shift to properly save expected_amount.")

# Add cash/momo breakdown to shift_details
old_details = '''            "expected_cash": float(getattr(shift, 'expected_amount', 0) or 0),
            "actual_cash": float(getattr(shift, 'actual_cash', 0) or 0),
            "variance": float(getattr(shift, 'variance', 0) or 0),
        },'''

new_details = '''            "opening_balance": float(shift.opening_balance),
            "expected_cash": float(getattr(shift, 'expected_amount', 0) or 0),
            "actual_cash": float(getattr(shift, 'actual_cash', 0) or 0),
            "variance": float(getattr(shift, 'variance', 0) or 0),
            "cash_sales": float(sum(inv.total for inv in invoices if inv.payment_method == "CASH")),
            "momo_sales": float(sum(inv.total for inv in invoices if inv.payment_method in ("MOMO", "MTN", "AIRTEL", "ZAMTEL"))),
            "total_sales": float(sum(inv.total for inv in invoices)),
        },'''

# Note: shift_details needs to fetch invoices to calculate this
old_details_query = '''    invoices = shift.invoices.filter(status="PAID")
    
    return Response({
        "shift": {'''
        
new_details_query = '''    invoices = shift.invoices.filter(status="PAID")
    
    return Response({
        "shift": {'''

if old_details in v_content:
    v_content = v_content.replace(old_details, new_details)
    print("✅ Added cash/momo breakdown to shift_details.")

views_path.write_text(v_content, encoding="utf-8")

# ============================================================
# 2. Update Shift History UI to show the math breakdown
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "shifts.html"
h_content = html_path.read_text(encoding="utf-8")

# Find the Financial Summary block in the View Details Modal
old_summary = '''          <!-- Financial Summary -->
          <div class="grid grid-cols-4 gap-4 mb-6 bg-gray-50 p-4 rounded-lg">
            <div>
              <div class="text-xs text-gray-500 uppercase">Expected Cash</div>
              <div class="font-bold text-lg" x-text="formatCurrency(selectedShift.shift.expected_cash)"></div>
            </div>
            <div>
              <div class="text-xs text-gray-500 uppercase">Actual Cash</div>
              <div class="font-bold text-lg" x-text="formatCurrency(selectedShift.shift.actual_cash)"></div>
            </div>
            <div>
              <div class="text-xs text-gray-500 uppercase">Variance</div>
              <div class="font-bold text-lg" :class="selectedShift.shift.variance < 0 ? 'text-red-600' : 'text-green-600'" x-text="formatCurrency(selectedShift.shift.variance)"></div>
            </div>
            <div>
              <div class="text-xs text-gray-500 uppercase">Total Sales</div>
              <div class="font-bold text-lg" x-text="formatCurrency(selectedShift.sales.reduce((s, i) => s + i.total, 0))"></div>
            </div>
          </div>'''

new_summary = '''          <!-- Financial Summary -->
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
          </div>'''

if old_summary in h_content:
    h_content = h_content.replace(old_summary, new_summary)
    html_path.write_text(h_content, encoding="utf-8")
    print("✅ Updated Shift History UI with detailed breakdown.")
else:
    print("⚠️ Could not find exact summary block. Checking for variations.")
    # Fallback to a simpler replace if the exact string changed
    h_content = re.sub(
        r"<!-- Financial Summary -->.*?x-text=\"formatCurrency\(selectedShift\.sales\.reduce.*?</div>\s*</div>",
        new_summary,
        h_content,
        flags=re.DOTALL
    )
    html_path.write_text(h_content, encoding="utf-8")
    print("✅ Updated Shift History UI using regex fallback.")

print("\n🎉 Done! Restart the server and refresh Shift History.")