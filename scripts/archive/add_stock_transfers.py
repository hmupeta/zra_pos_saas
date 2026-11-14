import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Inventory Models
# ============================================================
models_path = BACKEND_PATH / "inventory" / "models.py"
content = models_path.read_text(encoding="utf-8")

if "class StockTransfer" not in content:
    content += '''

class StockTransfer(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    transfer_number = models.CharField(max_length=50, unique=True)
    from_company = models.ForeignKey("core.Company", on_delete=models.PROTECT, related_name="transfers_out")
    to_company = models.ForeignKey("core.Company", on_delete=models.PROTECT, related_name="transfers_in")
    status = models.CharField(max_length=20, default="COMPLETED") # DRAFT, COMPLETED
    created_by = models.ForeignKey("core.User", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transfer_number

class StockTransferItem(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
'''
    models_path.write_text(content, encoding="utf-8")
print("✅ Added StockTransfer models")

# ============================================================
# 2. Update Inventory Views
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

transfer_views = '''
from .models import StockTransfer, StockTransferItem
from core.models import Company

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def transfers_list(request):
    if request.method == "GET":
        qs = StockTransfer.objects.filter(tenant=request.tenant).order_by("-created_at")
        return Response([{
            "id": t.id, "transfer_number": t.transfer_number,
            "from_branch": t.from_company.name, "to_branch": t.to_company.name,
            "date": t.created_at.strftime("%Y-%m-%d %H:%M"),
            "status": t.status
        } for t in qs])

    # POST: Create Transfer
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    from_id = data.get("from_company_id")
    to_id = data.get("to_company_id")
    items = data.get("items", [])

    if from_id == to_id:
        return Response({"error": "Source and destination cannot be the same"}, status=400)
    if not items:
        return Response({"error": "No items selected"}, status=400)

    import datetime
    ref = f"TRF-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

    transfer = StockTransfer.objects.create(
        tenant=request.tenant, transfer_number=ref,
        from_company_id=from_id, to_company_id=to_id,
        created_by=request.user
    )

    for item in items:
        # 1. Deduct from Source Branch
        try:
            source_prod = Product.objects.get(id=item["product_id"], company_id=from_id)
            qty = Decimal(str(item["quantity"]))
            
            if source_prod.current_stock < qty:
                transfer.delete() # Rollback
                return Response({"error": f"Not enough stock for {source_prod.name}"}, status=400)
                
            source_prod.current_stock -= qty
            source_prod.save()
        except Product.DoesNotExist:
            transfer.delete()
            return Response({"error": "Source product not found"}, status=404)

        # 2. Add to Destination Branch
        # We match the product in the destination branch by barcode
        dest_prod, created = Product.objects.get_or_create(
            tenant=request.tenant, company_id=to_id, barcode=source_prod.barcode,
            defaults={
                "name": source_prod.name, "category": source_prod.category,
                "tax_rate": source_prod.tax_rate, "unit_cost": source_prod.unit_cost,
                "selling_price": source_prod.selling_price, "zra_item_code": source_prod.zra_item_code
            }
        )
        dest_prod.current_stock += qty
        dest_prod.save()

        # 3. Record Transfer Item
        StockTransferItem.objects.create(
            transfer=transfer, product=source_prod, quantity=qty
        )

    return Response({"success": True, "transfer_number": ref})
'''

if "def transfers_list" not in v_content:
    views_path.write_text(v_content + "\n\n" + transfer_views, encoding="utf-8")

# Update URLs
urls_path = BACKEND_PATH / "inventory" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "transfers_list" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("transfers/", views.transfers_list, name="transfers_list"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Added Stock Transfer API")

# ============================================================
# 3. Add Frontend Route & Nav
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")
if "def transfers_page" not in web_content:
    web_content += "\n\ndef transfers_page(request):\n    return render(request, 'pos/transfers.html')\n"
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/transfers" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('transfers', views_web.transfers_page, name='transfers_page'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")
if "href=\"/transfers\"" not in nav_content:
    nav_content = nav_content.replace(
        '<a href="/barcodes" class="nav-link"',
        '<a href="/transfers" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)"><i data-lucide="arrow-right-left" class="w-4 h-4 mr-3"></i> Stock Transfers</a>\n    <a href="/barcodes" class="nav-link"'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Stock Transfers to Sidebar")

# ============================================================
# 4. Create the UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "transfers.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Stock Transfers{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="transfersApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Stock Transfers</h1>
        <p class="text-gray-500 text-sm mt-1">Move inventory between branches.</p>
      </div>
      <button @click="showModal = true" class="btn-primary">+ New Transfer</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Transfer #</th>
            <th class="px-4 py-3">Date</th>
            <th class="px-4 py-3">From Branch</th>
            <th class="px-4 py-3">To Branch</th>
            <th class="px-4 py-3 text-center">Status</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="t in transfers" :key="t.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-mono text-xs" x-text="t.transfer_number"></td>
              <td class="px-4 py-3 text-gray-500" x-text="t.date"></td>
              <td class="px-4 py-3 font-medium text-slate-700" x-text="t.from_branch"></td>
              <td class="px-4 py-3 font-medium text-slate-700" x-text="t.to_branch"></td>
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded text-xs bg-green-100 text-green-700" x-text="t.status"></span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="transfers.length === 0" class="p-8 text-center text-gray-400">No transfers found.</div>
    </div>

    <!-- New Transfer Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-2xl w-full p-6 max-h-[90vh] flex flex-col">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">New Stock Transfer</h2>
            <button @click="showModal = false" class="text-gray-400 hover:text-gray-800"><i data-lucide="x" class="w-6 h-6"></i></button>
          </div>

          <form @submit.prevent="submitTransfer()" class="flex-1 flex flex-col overflow-hidden">
            <div class="grid grid-cols-2 gap-4 mb-4">
              <div>
                <label class="block text-sm mb-1">From Branch (Source)</label>
                <select x-model="form.from_company_id" @change="loadProducts()" class="input-field" required>
                  <option value="">Select Source...</option>
                  <template x-for="b in branches" :key="b.id">
                    <option :value="b.id" x-text="b.name"></option>
                  </template>
                </select>
              </div>
              <div>
                <label class="block text-sm mb-1">To Branch (Destination)</label>
                <select x-model="form.to_company_id" class="input-field" required>
                  <option value="">Select Destination...</option>
                  <template x-for="b in branches" :key="b.id">
                    <option :value="b.id" x-text="b.name"></option>
                  </template>
                </select>
              </div>
            </div>

            <div class="flex-1 overflow-y-auto border rounded p-2 mb-4 bg-gray-50">
              <table class="w-full text-sm">
                <thead><tr><th class="text-left pb-2">Product</th><th class="text-right pb-2">Available</th><th class="text-right pb-2">Qty to Transfer</th></tr></thead>
                <tbody>
                  <template x-for="(line, idx) in form.lines" :key="idx">
                    <tr>
                      <td class="pr-2">
                        <select x-model="line.product_id" class="input-field text-sm py-1" required>
                          <option value="">Select Product...</option>
                          <template x-for="p in sourceProducts" :key="p.id">
                            <option :value="p.id" x-text="p.name + ' (' + p.barcode + ')'"></option>
                          </template>
                        </select>
                      </td>
                      <td class="pr-2 text-right text-gray-500 text-xs">
                        <span x-text="getAvailable(line.product_id)"></span>
                      </td>
                      <td><input type="number" step="0.01" x-model="line.quantity" class="input-field text-sm py-1 text-right" required></td>
                    </tr>
                  </template>
                </tbody>
              </table>
              <button type="button" @click="form.lines.push({product_id:'', quantity:''})" class="text-sm text-brand-600 mt-2 hover:underline">+ Add Another Product</button>
            </div>

            <div class="flex justify-end gap-2 border-t pt-4">
              <button type="button" @click="showModal = false" class="btn-secondary">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="saving">Complete Transfer</button>
            </div>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function transfersApp() {
  return {
    transfers: [], branches: [], sourceProducts: [], showModal: false, saving: false,
    form: { from_company_id: '', to_company_id: '', lines: [{product_id:'', quantity:''}] },

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.transfers = await apiFetch('/inventory/transfers/');
        this.branches = await apiFetch('/auth/branches/');
      } catch(e) { alert(e.message); }
    },

    async loadProducts() {
      this.form.lines = [{product_id:'', quantity:''}];
      this.sourceProducts = [];
      if (!this.form.from_company_id) return;
      
      try {
        // We need a custom endpoint or query to get products for a specific branch
        // For now, let's assume the API accepts a branch_id query param. 
        // If it doesn't, we temporarily use a modified fetch.
        const res = await apiFetch(`/inventory/products/?branch_id=${this.form.from_company_id}`);
        this.sourceProducts = res;
      } catch(e) { console.error(e); }
    },

    getAvailable(productId) {
      const p = this.sourceProducts.find(x => x.id == productId);
      return p ? p.current_stock : '-';
    },

    async submitTransfer() {
      this.saving = true;
      try {
        const res = await apiFetch('/inventory/transfers/', { method: 'POST', body: JSON.stringify(this.form) });
        alert('Transfer completed successfully!');
        this.showModal = false;
        this.form = { from_company_id: '', to_company_id: '', lines: [{product_id:'', quantity:''}] };
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created transfers.html UI")

# ============================================================
# 5. Patch Products API to allow fetching by branch_id
# ============================================================
v_content = views_path.read_text(encoding="utf-8")
old_query = '''        search = request.query_params.get('search', '')
        products = Product.objects.filter(tenant=request.tenant, company=request.branch, is_active=True)'''
new_query = '''        search = request.query_params.get('search', '')
        target_branch = request.query_params.get('branch_id', request.branch.id)
        products = Product.objects.filter(tenant=request.tenant, company_id=target_branch, is_active=True)'''
v_content = v_content.replace(old_query, new_query)
views_path.write_text(v_content, encoding="utf-8")
print("✅ Updated Products API to allow filtering by branch_id")

# ============================================================
# 6. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "inventory"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")