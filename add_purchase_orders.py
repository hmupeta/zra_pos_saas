import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Models (Add PO Items)
# ============================================================
models_path = BACKEND_PATH / "purchasing" / "models.py"
content = models_path.read_text(encoding="utf-8")

if "class PurchaseOrderItem" not in content:
    content += '''

class PurchaseOrderItem(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
'''
    models_path.write_text(content, encoding="utf-8")
print("✅ Added PurchaseOrderItem model")

# ============================================================
# 2. Update Views (Create PO, List POs, Receive PO)
# ============================================================
views_path = BACKEND_PATH / "purchasing" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

po_views = '''
from django.utils import timezone
from .models import PurchaseOrder, PurchaseOrderItem

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def purchase_orders_list(request):
    if request.method == "GET":
        qs = PurchaseOrder.objects.filter(tenant=request.tenant).order_by("-order_date")
        return Response([{
            "id": po.id, "po_number": po.po_number, "supplier": po.supplier.name,
            "date": po.order_date.strftime("%Y-%m-%d"), "total": float(po.total),
            "status": po.status
        } for po in qs])

    # Create New PO
    data = request.data
    items = data.get("items", [])
    if not items:
        return Response({"error": "PO must have items"}, status=400)

    import datetime
    po_num = f"PO-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
    
    po = PurchaseOrder.objects.create(
        tenant=request.tenant, company=request.branch,
        supplier_id=data["supplier_id"], po_number=po_num,
        created_by=request.user
    )

    total = Decimal("0")
    for item in items:
        qty = Decimal(str(item["quantity"]))
        cost = Decimal(str(item["unit_cost"]))
        total += (qty * cost)
        PurchaseOrderItem.objects.create(
            po=po, product_id=item["product_id"],
            quantity=qty, unit_cost=cost
        )

    po.total = total
    po.save()

    return Response({"success": True, "id": po.id, "po_number": po.po_number})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def po_details(request, pk):
    try:
        po = PurchaseOrder.objects.get(pk=pk, tenant=request.tenant)
    except PurchaseOrder.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
        
    return Response({
        "id": po.id, "po_number": po.po_number, "supplier": po.supplier.name,
        "status": po.status, "total": float(po.total),
        "items": [{
            "id": i.id, "product_id": i.product_id, "product": i.product.name,
            "quantity": float(i.quantity), "unit_cost": float(i.unit_cost)
        } for i in po.items.all()]
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def receive_po(request, pk):
    """Marks PO as RECEIVED and adds inventory."""
    try:
        po = PurchaseOrder.objects.get(pk=pk, tenant=request.tenant, status="DRAFT")
    except PurchaseOrder.DoesNotExist:
        return Response({"error": "PO not found or already received"}, status=400)

    for item in po.items.all():
        product = item.product
        product.current_stock += item.quantity
        product.save()

    po.status = "RECEIVED"
    po.save()
    return Response({"success": True})
'''

if "def purchase_orders_list" not in v_content:
    views_path.write_text(v_content + "\n\n" + po_views, encoding="utf-8")
print("✅ Added Purchase Order Views")

# ============================================================
# 3. Update URLs
# ============================================================
urls_path = BACKEND_PATH / "purchasing" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "purchase_orders_list" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path('po/', views.purchase_orders_list, name='purchase_orders_list'),
    path('po/<int:pk>/', views.po_details, name='po_details'),
    path('po/<int:pk>/receive/', views.receive_po, name='receive_po'),'''
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Updated purchasing/urls.py")

# ============================================================
# 4. Update Frontend (purchasing.html)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "purchasing.html"
h_content = html_path.read_text(encoding="utf-8")

# Add PO section to the UI (above the current layout)
po_html = '''
    <!-- Purchase Orders Section -->
    <div class="card p-6 mb-6">
      <div class="flex justify-between items-center mb-4 border-b pb-4">
        <h2 class="text-lg font-bold">Purchase Orders (Stock Orders)</h2>
        <button @click="showPoModal = true" class="btn-primary text-sm">+ Create Purchase Order</button>
      </div>
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase">
          <tr><th class="p-2">PO #</th><th class="p-2">Supplier</th><th class="p-2">Date</th><th class="p-2">Total</th><th class="p-2 text-center">Status</th><th class="p-2 text-right">Action</th></tr>
        </thead>
        <tbody>
          <template x-for="po in pos" :key="po.id">
            <tr class="border-t hover:bg-gray-50 cursor-pointer" @click="viewPo(po)">
              <td class="p-2 font-mono text-xs" x-text="po.po_number"></td>
              <td class="p-2 font-medium" x-text="po.supplier"></td>
              <td class="p-2 text-gray-500" x-text="po.date"></td>
              <td class="p-2 font-bold" x-text="formatCurrency(po.total)"></td>
              <td class="p-2 text-center">
                <span class="px-2 py-0.5 rounded text-xs" :class="po.status === 'DRAFT' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'" x-text="po.status"></span>
              </td>
              <td class="p-2 text-right">
                <button @click.stop="viewPo(po)" class="text-brand-600 hover:underline text-xs">View</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
'''
h_content = h_content.replace('<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">', po_html + '\n    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">')

# Add PO View Modal
po_modal = '''
    <!-- View PO Modal -->
    <template x-if="selectedPo">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-2xl w-full p-6">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold" x-text="'PO: ' + selectedPo.po_number"></h2>
            <button @click="selectedPo = null" class="text-gray-500 hover:text-gray-800">✕</button>
          </div>
          
          <div class="flex justify-between mb-4 bg-gray-50 p-3 rounded">
            <div><span class="text-gray-500 text-sm">Supplier:</span> <span class="font-bold" x-text="selectedPo.supplier"></span></div>
            <div><span class="text-gray-500 text-sm">Total:</span> <span class="font-bold" x-text="formatCurrency(selectedPo.total)"></span></div>
            <div><span class="text-gray-500 text-sm">Status:</span> <span class="font-bold" x-text="selectedPo.status"></span></div>
          </div>

          <table class="w-full text-sm mb-6">
            <thead class="bg-gray-100 text-left text-xs uppercase">
              <tr><th class="p-2">Product</th><th class="p-2 text-right">Qty</th><th class="p-2 text-right">Cost</th><th class="p-2 text-right">Total</th></tr>
            </thead>
            <tbody>
              <template x-for="item in selectedPo.items" :key="item.id">
                <tr class="border-t">
                  <td class="p-2" x-text="item.product"></td>
                  <td class="p-2 text-right" x-text="item.quantity"></td>
                  <td class="p-2 text-right" x-text="formatCurrency(item.unit_cost)"></td>
                  <td class="p-2 text-right font-bold" x-text="formatCurrency(item.quantity * item.unit_cost)"></td>
                </tr>
              </template>
            </tbody>
          </table>

          <div class="flex justify-end" x-show="selectedPo.status === 'DRAFT'">
            <button @click="receivePo(selectedPo.id)" class="btn-primary bg-green-600 hover:bg-green-700">Receive Goods & Update Stock</button>
          </div>
        </div>
      </div>
    </template>

    <!-- Create PO Modal -->
    <template x-if="showPoModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-2xl w-full p-6 max-h-[90vh] overflow-y-auto">
          <h2 class="text-xl font-bold mb-4">New Purchase Order</h2>
          <form @submit.prevent="createPo()" class="space-y-4">
            <select x-model="poForm.supplier_id" class="input-field" required>
              <option value="">Select Supplier...</option>
              <template x-for="s in suppliers" :key="s.id">
                <option :value="s.id" x-text="s.name"></option>
              </template>
            </select>

            <table class="w-full text-sm">
              <thead><tr><th class="text-left pb-2">Product</th><th class="text-right pb-2">Qty</th><th class="text-right pb-2">Unit Cost</th></tr></thead>
              <tbody>
                <template x-for="(line, idx) in poForm.lines" :key="idx">
                  <tr>
                    <td class="pr-2">
                      <select x-model="line.product_id" class="input-field" required>
                        <option value="">Select...</option>
                        <template x-for="p in products" :key="p.id">
                          <option :value="p.id" x-text="p.name"></option>
                        </template>
                      </select>
                    </td>
                    <td class="pr-2"><input type="number" x-model="line.quantity" class="input-field text-right" required></td>
                    <td><input type="number" step="0.01" x-model="line.unit_cost" class="input-field text-right" required></td>
                  </tr>
                </template>
              </tbody>
            </table>
            <button type="button" @click="poForm.lines.push({product_id:'', quantity:'', unit_cost:''})" class="text-sm text-brand-600 mb-4 hover:underline">+ Add Line</button>

            <div class="flex justify-end gap-2 border-t pt-4">
              <button type="button" @click="showPoModal = false" class="btn-secondary">Cancel</button>
              <button type="submit" class="btn-primary">Create PO</button>
            </div>
          </form>
        </div>
      </div>
    </template>
'''
h_content = h_content.replace("  </div>\n</div>\n<script>", po_modal + "\n  </div>\n</div>\n<script>")

# Update JS
h_content = h_content.replace(
    "suppliers: [], invoices: [],",
    "suppliers: [], invoices: [], pos: [], products: [], selectedPo: null, showPoModal: false,\n    poForm: { supplier_id: '', lines: [{product_id:'', quantity:'', unit_cost:''}] },"
)

new_po_js = '''
    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.suppliers = await apiFetch('/purchasing/suppliers/');
        this.invoices = await apiFetch('/purchasing/invoices/');
        this.pos = await apiFetch('/purchasing/po/');
        this.products = await apiFetch('/inventory/products/');
      } catch(e) { alert(e.message); }
    },

    async createPo() {
      try {
        await apiFetch('/purchasing/po/', { method: 'POST', body: JSON.stringify(this.poForm) });
        this.showPoModal = false;
        this.poForm = { supplier_id: '', lines: [{product_id:'', quantity:'', unit_cost:''}] };
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },

    async viewPo(po) {
      try { this.selectedPo = await apiFetch(`/purchasing/po/${po.id}/`); } catch(e) { alert(e.message); }
    },

    async receivePo(id) {
      if (!confirm('Are you sure you received these goods? This will update inventory.')) return;
      try {
        await apiFetch(`/purchasing/po/${id}/receive/`, { method: 'POST' });
        alert('Goods received and stock updated!');
        this.selectedPo = null;
        this.load();
      } catch(e) { alert(e.message); }
    },
'''
h_content = h_content.replace("    async load() {\n      if (!requireAuth() || !requireBranch()) return;\n      try {\n        this.suppliers = await apiFetch('/purchasing/suppliers/');\n        this.invoices = await apiFetch('/purchasing/invoices/');\n      } catch(e) { alert(e.message); }\n    },", new_po_js)

html_path.write_text(h_content, encoding="utf-8")
print("✅ Updated purchasing.html with PO features")

# ============================================================
# 5. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "purchasing"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")