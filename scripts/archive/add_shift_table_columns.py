import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Backend to send sales breakdown to the list view
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
        invoices = s.invoices.filter(status="PAID")
        
        # Calculate breakdown
        total_sales = sum(inv.total for inv in invoices)
        cash_sales = sum(inv.total for inv in invoices if inv.payment_method == "CASH")
        momo_sales = sum(inv.total for inv in invoices if inv.payment_method in ("MOMO", "MTN", "AIRTEL", "ZAMTEL"))
        
        expected_cash = s.opening_balance + cash_sales
        saved_actual = getattr(s, 'actual_cash', 0) or 0
        recalculated_variance = saved_actual - expected_cash
        
        data.append({
            "id": s.id,
            "cashier": s.cashier.username,
            "opening_time": s.opening_time.strftime("%Y-%m-%d %H:%M"),
            "closing_time": s.closing_time.strftime("%H:%M") if s.closing_time else "OPEN",
            "opening_balance": float(s.opening_balance),
            "total_sales": float(total_sales),
            "cash_sales": float(cash_sales),
            "momo_sales": float(momo_sales),
            "expected_cash": float(expected_cash),
            "actual_cash": float(saved_actual),
            "variance": float(recalculated_variance),
            "is_closed": s.is_closed
        })
    return Response(data)
'''

# Replace the shifts_list function
pattern = r"@api_view\(\[\"GET\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef shifts_list\(request\):.*?return Response\(data\)"
if re.search(pattern, v_content, flags=re.DOTALL):
    v_content = re.sub(pattern, new_list_view.strip(), v_content, flags=re.DOTALL)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Backend updated to send sales breakdown.")
else:
    print("⚠️ Could not find shifts_list. Please check sales/views.py manually.")

# ============================================================
# 2. Update Frontend Table Columns
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "shifts.html"
h_content = html_path.read_text(encoding="utf-8")

# Replace the Table Header
old_thead = '''        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Cashier</th>
            <th class="px-4 py-3">Date Opened</th>
            <th class="px-4 py-3">Time Closed</th>
            <th class="px-4 py-3 text-right">Expected Cash</th>
            <th class="px-4 py-3 text-right">Actual Cash</th>
            <th class="px-4 py-3 text-right">Variance</th>
            <th class="px-4 py-3 text-center">Status</th>
            <th class="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>'''

new_thead = '''        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Cashier</th>
            <th class="px-4 py-3">Date Opened</th>
            <th class="px-4 py-3">Time Closed</th>
            <th class="px-4 py-3 text-right font-bold text-brand-700">Total Sales</th>
            <th class="px-4 py-3 text-right text-green-600">Cash Sales</th>
            <th class="px-4 py-3 text-right text-yellow-600">MoMo Sales</th>
            <th class="px-4 py-3 text-right border-l">Expected Cash</th>
            <th class="px-4 py-3 text-right">Actual Cash</th>
            <th class="px-4 py-3 text-right">Variance</th>
            <th class="px-4 py-3 text-center">Status</th>
            <th class="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>'''

if old_thead in h_content:
    h_content = h_content.replace(old_thead, new_thead)
    print("✅ Updated Table Header.")

# Replace the Table Row (tbody)
old_tbody = '''          <template x-for="s in shifts" :key="s.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-medium text-slate-800" x-text="s.cashier"></td>
              <td class="px-4 py-3 text-gray-500" x-text="s.opening_time"></td>
              <td class="px-4 py-3 text-gray-500" x-text="s.closing_time"></td>
              <td class="px-4 py-3 text-right" x-text="formatCurrency(s.expected_cash)"></td>
              <td class="px-4 py-3 text-right font-bold" x-text="s.is_closed ? formatCurrency(s.actual_cash) : '-'"></td>
              <td class="px-4 py-3 text-right font-bold" 
                  :class="s.variance < 0 ? 'text-red-600' : s.variance > 0 ? 'text-green-600' : 'text-gray-400'" 
                  x-text="s.is_closed ? formatCurrency(s.variance) : '-'"></td>
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded text-xs font-medium" 
                      :class="s.is_closed ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-700 animate-pulse'" 
                      x-text="s.is_closed ? 'Closed' : 'Active'"></span>
              </td>
              <td class="px-4 py-3 text-right">
                <button @click="viewDetails(s.id)" class="text-brand-600 hover:underline text-xs">View Report</button>
              </td>
            </tr>
          </template>'''

new_tbody = '''          <template x-for="s in shifts" :key="s.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-medium text-slate-800" x-text="s.cashier"></td>
              <td class="px-4 py-3 text-gray-500" x-text="s.opening_time"></td>
              <td class="px-4 py-3 text-gray-500" x-text="s.closing_time"></td>
              
              <!-- Sales Breakdown -->
              <td class="px-4 py-3 text-right font-bold text-brand-700" x-text="formatCurrency(s.total_sales)"></td>
              <td class="px-4 py-3 text-right font-medium text-green-700" x-text="formatCurrency(s.cash_sales)"></td>
              <td class="px-4 py-3 text-right font-medium text-yellow-600" x-text="formatCurrency(s.momo_sales)"></td>
              
              <!-- Cash Reconciliation -->
              <td class="px-4 py-3 text-right border-l" x-text="formatCurrency(s.expected_cash)"></td>
              <td class="px-4 py-3 text-right font-bold" x-text="s.is_closed ? formatCurrency(s.actual_cash) : '-'"></td>
              <td class="px-4 py-3 text-right font-bold" 
                  :class="s.variance < 0 ? 'text-red-600' : s.variance > 0 ? 'text-green-600' : 'text-gray-400'" 
                  x-text="s.is_closed ? formatCurrency(s.variance) : '-'"></td>
              
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded text-xs font-medium" 
                      :class="s.is_closed ? 'bg-gray-100 text-gray-600' : 'bg-green-100 text-green-700 animate-pulse'" 
                      x-text="s.is_closed ? 'Closed' : 'Active'"></span>
              </td>
              <td class="px-4 py-3 text-right">
                <button @click="viewDetails(s.id)" class="text-brand-600 hover:underline text-xs">View Report</button>
              </td>
            </tr>
          </template>'''

if old_tbody in h_content:
    h_content = h_content.replace(old_tbody, new_tbody)
    print("✅ Updated Table Rows.")
else:
    print("⚠️ Could not find exact row block. Please check shifts.html manually.")

# Update the colspan for the "No shifts found" message (was 8, now 11)
h_content = h_content.replace('colspan="8"', 'colspan="11"')

html_path.write_text(h_content, encoding="utf-8")

print("\n🎉 Done! Restart the server and do a HARD REFRESH on Shift History.")