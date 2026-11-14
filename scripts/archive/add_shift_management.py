import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Backend Views (List Shifts & Details)
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

shift_views = '''
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shifts_list(request):
    """List all shifts for this branch."""
    qs = Shift.objects.filter(tenant=request.tenant, company=request.branch).order_by("-opening_time")
    
    return Response([{
        "id": s.id,
        "cashier": s.cashier.username,
        "opening_time": s.opening_time.strftime("%Y-%m-%d %H:%M"),
        "closing_time": s.closing_time.strftime("%H:%M") if s.closing_time else "OPEN",
        "opening_balance": float(s.opening_balance),
        "expected_cash": float(s.expected_amount or 0),
        "actual_cash": float(s.actual_cash or 0),
        "variance": float(s.variance or 0),
        "is_closed": s.is_closed
    } for s in qs[:100]])

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shift_details(request, pk):
    """Get details of a specific shift, including all its sales."""
    try:
        shift = Shift.objects.get(pk=pk, tenant=request.tenant)
    except Shift.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
        
    invoices = shift.invoices.filter(status="PAID")
    
    return Response({
        "shift": {
            "id": shift.id,
            "cashier": shift.cashier.username,
            "opening_time": shift.opening_time.strftime("%Y-%m-%d %H:%M"),
            "closing_time": shift.closing_time.strftime("%Y-%m-%d %H:%M") if shift.closing_time else None,
            "opening_balance": float(shift.opening_balance),
            "expected_cash": float(shift.expected_amount or 0),
            "actual_cash": float(shift.actual_cash or 0),
            "variance": float(shift.variance or 0),
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

if "def shifts_list" not in v_content:
    views_path.write_text(v_content + "\n\n" + shift_views, encoding="utf-8")

# Update URLs
urls_path = BACKEND_PATH / "sales" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "shifts_list" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path("shifts/", views.shifts_list, name="shifts_list"),
    path("shifts/<int:pk>/", views.shift_details, name="shift_details"),'''
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Added Shift API endpoints")

# ============================================================
# 2. Add Frontend Route & Nav
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")
if "def shifts_page" not in web_content:
    web_content += "\n\ndef shifts_page(request):\n    return render(request, 'pos/shifts.html')\n"
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/shifts" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('shifts', views_web.shifts_page, name='shifts_page'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")
if "href=\"/shifts\"" not in nav_content:
    nav_content = nav_content.replace(
        '<a href="/returns" class="nav-link">',
        '<a href="/shifts" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)"><i data-lucide="clock" class="w-4 h-4 mr-3"></i> Shift History</a>\n    <a href="/returns" class="nav-link">'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Shift History to Sidebar")

# ============================================================
# 3. Create the UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "shifts.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Shift History{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="shiftsApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Shift History</h1>
        <p class="text-gray-500 text-sm mt-1">View cashier Z-reports and cash drawer reconciliation.</p>
      </div>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
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
        </thead>
        <tbody>
          <template x-for="s in shifts" :key="s.id">
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
          </template>
        </tbody>
      </table>
      <div x-show="shifts.length === 0" class="p-8 text-center text-gray-400">No shifts found.</div>
    </div>

    <!-- View Details Modal -->
    <template x-if="selectedShift">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-3xl w-full p-6 max-h-[90vh] flex flex-col">
          
          <div class="flex justify-between items-center mb-6 border-b pb-4">
            <div>
              <h2 class="text-xl font-bold">Z-Report: <span x-text="selectedShift.shift.cashier"></span></h2>
              <p class="text-sm text-gray-500" x-text="selectedShift.shift.opening_time + ' to ' + (selectedShift.shift.closing_time || 'Present')"></p>
            </div>
            <button @click="selectedShift = null" class="text-gray-400 hover:text-gray-800"><i data-lucide="x" class="w-6 h-6"></i></button>
          </div>

          <!-- Financial Summary -->
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
          </div>

          <!-- Sales List -->
          <div class="flex-1 overflow-y-auto border rounded-lg">
            <table class="w-full text-sm">
              <thead class="bg-gray-100 sticky top-0 text-left text-xs uppercase text-gray-500">
                <tr><th class="px-4 py-2">Time</th><th class="px-4 py-2">Invoice</th><th class="px-4 py-2">Customer</th><th class="px-4 py-2">Method</th><th class="px-4 py-2 text-right">Total</th></tr>
              </thead>
              <tbody>
                <template x-for="sale in selectedShift.sales" :key="sale.invoice_number">
                  <tr class="border-t">
                    <td class="px-4 py-2 text-gray-500" x-text="sale.time"></td>
                    <td class="px-4 py-2 font-mono text-xs" x-text="sale.invoice_number"></td>
                    <td class="px-4 py-2" x-text="sale.customer"></td>
                    <td class="px-4 py-2"><span class="px-2 py-0.5 bg-gray-100 rounded text-xs" x-text="sale.payment_method"></span></td>
                    <td class="px-4 py-2 text-right font-medium" x-text="formatCurrency(sale.total)"></td>
                  </tr>
                </template>
              </tbody>
            </table>
            <div x-show="selectedShift.sales.length === 0" class="p-6 text-center text-gray-400">No sales during this shift.</div>
          </div>

        </div>
      </div>
    </template>

  </div>
</div>
<script>
function shiftsApp() {
  return {
    shifts: [], selectedShift: null,

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.shifts = await apiFetch('/sales/shifts/');
      } catch(e) { alert(e.message); }
    },

    async viewDetails(id) {
      try {
        this.selectedShift = await apiFetch(`/sales/shifts/${id}/`);
        setTimeout(() => { lucide.createIcons(); }, 50);
      } catch(e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created shifts.html UI")

print("\n🎉 Done! Restart the server.")