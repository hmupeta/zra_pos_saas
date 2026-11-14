import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Backend: Add endpoint to update actual cash
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

reconcile_view = '''
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reconcile_shift(request, pk):
    """Allows managers to retroactively fix the cash count for a closed shift."""
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER", "ADMIN"):
        return Response({"error": "Insufficient permissions"}, status=403)

    try:
        shift = Shift.objects.get(pk=pk, tenant=request.tenant)
    except Shift.DoesNotExist:
        return Response({"error": "Shift not found"}, status=404)

    if not shift.is_closed:
        return Response({"error": "Cannot reconcile an active shift"}, status=400)

    actual_cash = Decimal(str(request.data.get("actual_cash", 0)))
    
    # Recalculate expected cash to ensure accuracy
    invoices = shift.invoices.filter(status="PAID")
    cash_sales = sum(inv.total for inv in invoices if inv.payment_method == "CASH")
    expected_cash = shift.opening_balance + cash_sales
    
    # Update shift
    shift.actual_cash = actual_cash
    shift.expected_amount = expected_cash
    shift.variance = actual_cash - expected_cash
    shift.save()

    # Optional: Post an accounting adjustment for the variance here
    # (You would add the JournalEntry logic similar to the close_shift view)

    return Response({
        "success": True, 
        "message": "Shift reconciled successfully",
        "new_variance": float(shift.variance)
    })
'''

if "def reconcile_shift" not in v_content:
    v_content += "\n\n" + reconcile_view
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Added reconcile_shift API endpoint.")

# Update URLs
urls_path = BACKEND_PATH / "sales" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "reconcile_shift" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("shifts/<int:pk>/reconcile/", views.reconcile_shift, name="reconcile_shift"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
    print("✅ Added reconcile URL route.")

# ============================================================
# 2. Frontend: Add Reconcile button and Modal to shifts.html
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "shifts.html"
h_content = html_path.read_text(encoding="utf-8")

# A. Add Reconcile button to the table row
old_actions = '''              <td class="px-4 py-3 text-right">
                <button @click="viewDetails(s.id)" class="text-brand-600 hover:underline text-xs">View Report</button>
              </td>'''
new_actions = '''              <td class="px-4 py-3 text-right space-x-2">
                <button @click="viewDetails(s.id)" class="text-brand-600 hover:underline text-xs font-medium">View</button>
                <button x-show="s.is_closed" @click="openReconcile(s)" class="text-orange-600 hover:underline text-xs font-medium">Reconcile</button>
              </td>'''
h_content = h_content.replace(old_actions, new_actions)

# B. Add the Reconcile Modal before the closing div
reconcile_modal = '''
    <!-- Reconcile Shift Modal -->
    <template x-if="reconcileModal">
      <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[9999] p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl max-w-sm w-full p-6 shadow-2xl">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">Reconcile Cash Drawer</h2>
            <button @click="reconcileModal = null" class="text-gray-400 hover:text-red-500 font-bold text-xl">&times;</button>
          </div>
          
          <div class="bg-gray-50 p-4 rounded-lg mb-4 text-sm">
            <div class="flex justify-between mb-1">
              <span class="text-gray-500">Expected Cash:</span>
              <span class="font-bold text-slate-800" x-text="formatCurrency(reconcileData.expected_cash)"></span>
            </div>
            <p class="text-xs text-gray-500 mt-2">Enter the physical cash you actually counted for this shift.</p>
          </div>

          <form @submit.prevent="submitReconcile()">
            <label class="block text-sm font-medium mb-1">Physical Cash Counted (K)</label>
            <input type="number" step="0.01" x-model="reconcileData.actual_cash" class="input-field text-lg font-bold mb-4" required>
            
            <div class="flex gap-2">
              <button type="button" @click="reconcileModal = null" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1 bg-orange-600 hover:bg-orange-700 text-white" :disabled="reconciling">
                <span x-show="!reconciling">Update</span>
                <span x-show="reconciling">Saving...</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </template>
'''
h_content = h_content.replace("  </div>\n</div>\n\n<script>", reconcile_modal + "\n  </div>\n</div>\n\n<script>")

# C. Add JS state and functions
h_content = h_content.replace(
    "shifts: [], selectedShift: null,",
    "shifts: [], selectedShift: null, reconcileModal: null, reconcileData: {}, reconciling: false,"
)

new_js_funcs = '''
    openReconcile(shift) {
      this.reconcileData = { 
        id: shift.id, 
        expected_cash: shift.expected_cash, 
        actual_cash: shift.actual_cash || shift.expected_cash // default to expected
      };
      this.reconcileModal = true;
    },

    async submitReconcile() {
      this.reconciling = true;
      try {
        const res = await apiFetch(`/sales/shifts/${this.reconcileData.id}/reconcile/`, {
          method: 'POST',
          body: JSON.stringify({ actual_cash: this.reconcileData.actual_cash })
        });
        
        alert(`✅ Shift updated. New variance: ${formatCurrency(res.new_variance)}`);
        this.reconcileModal = null;
        this.load(); // Refresh table
      } catch(e) {
        alert(e.response?.data?.error || e.message);
      } finally {
        this.reconciling = false;
      }
    },
'''
h_content = h_content.replace("    async viewDetails(id) {", new_js_funcs + "\n    async viewDetails(id) {")

html_path.write_text(h_content, encoding="utf-8")
print("✅ Updated Shift History UI with Reconcile functionality.")

print("\n🎉 Done! Restart the server and do a HARD REFRESH on Shift History.")