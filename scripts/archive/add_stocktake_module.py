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

if "class StockTake" not in content:
    content += '''

class StockTake(models.Model):
    STATUS = [
        ("DRAFT", "Draft (Counting)"),
        ("PENDING", "Pending Manager Approval"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    reference = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    counted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stocktakes_counted")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="stocktakes_approved")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.reference

class StockTakeItem(models.Model):
    stocktake = models.ForeignKey(StockTake, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    system_qty = models.DecimalField(max_digits=10, decimal_places=2)
    counted_qty = models.DecimalField(max_digits=10, decimal_places=2)
    variance = models.DecimalField(max_digits=10, decimal_places=2) # counted - system

    def save(self, *args, **kwargs):
        self.variance = self.counted_qty - self.system_qty
        super().save(*args, **kwargs)
'''
    models_path.write_text(content, encoding="utf-8")
print("✅ Added StockTake models")

# ============================================================
# 2. Update Inventory Views
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
views_content = views_path.read_text(encoding="utf-8")

stocktake_views = '''
from .models import StockTake, StockTakeItem
from accounting.models import Account, Journal, JournalLine
from django.utils import timezone
import datetime

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def stocktakes_list(request):
    if request.method == "GET":
        qs = StockTake.objects.filter(tenant=request.tenant).order_by("-created_at")
        return Response([{
            "id": s.id, "reference": s.reference, "status": s.status,
            "counted_by": s.counted_by.username, "approved_by": s.approved_by.username if s.approved_by else None,
            "date": s.created_at.strftime("%Y-%m-%d %H:%M"),
            "items_count": s.items.count()
        } for s in qs])

    # POST: Create new
    ref = f"ST-{datetime.datetime.now().strftime('%y%m%d%H%M')}"
    st = StockTake.objects.create(
        tenant=request.tenant, company=request.branch,
        reference=ref, counted_by=request.user
    )
    return Response({"success": True, "id": st.id, "reference": ref})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def stocktake_detail(request, pk):
    try:
        st = StockTake.objects.get(pk=pk, tenant=request.tenant)
    except StockTake.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
    
    items = st.items.all().select_related("product")
    return Response({
        "id": st.id, "reference": st.reference, "status": st.status,
        "items": [{
            "id": i.id, "barcode": i.product.barcode, "name": i.product.name,
            "system_qty": float(i.system_qty), "counted_qty": float(i.counted_qty), "variance": float(i.variance)
        } for i in items]
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def stocktake_scan(request, pk):
    """Add or update an item in the stocktake by barcode."""
    barcode = request.data.get("barcode")
    counted_qty = request.data.get("counted_qty")
    
    try:
        st = StockTake.objects.get(pk=pk, tenant=request.tenant, status="DRAFT")
        product = Product.objects.get(barcode=barcode, tenant=request.tenant)
        
        # Update if exists, else create
        item, created = StockTakeItem.objects.get_or_create(
            stocktake=st, product=product,
            defaults={"system_qty": product.current_stock, "counted_qty": counted_qty}
        )
        if not created:
            item.counted_qty = counted_qty
            item.save()
            
        return Response({"success": True, "name": product.name, "variance": float(item.variance)})
    except Product.DoesNotExist:
        return Response({"error": "Barcode not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def stocktake_submit(request, pk):
    st = StockTake.objects.get(pk=pk, tenant=request.tenant)
    if not st.items.exists():
        return Response({"error": "Cannot submit empty count"}, status=400)
    st.status = "PENDING"
    st.save()
    return Response({"success": True})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def stocktake_approve(request, pk):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Only Managers can approve stock counts"}, status=403)
        
    try:
        st = StockTake.objects.get(pk=pk, tenant=request.tenant, status="PENDING")
    except StockTake.DoesNotExist:
        return Response({"error": "Invalid or already approved"}, status=400)

    # 1. Update Stock and Record Movements
    for item in st.items.all():
        diff = item.counted_qty - item.system_qty
        if diff != 0:
            product = item.product
            product.current_stock = item.counted_qty
            product.save()
            
            StockMovement.objects.create(
                product=product, quantity=diff, movement_type="ADJUST",
                reference=st.reference, notes="Stocktake Adjustment", created_by=request.user
            )

    # 2. Accounting Journal for the Total Variance Value
    total_variance_value = sum((item.variance * item.product.unit_cost for item in st.items.all()))
    
    if total_variance_value != 0:
        inv_account = Account.objects.filter(tenant=request.tenant, code="1200").first() # Inventory
        shrink_account = Account.objects.filter(tenant=request.tenant, code="5900").first() # Shrinkage/Misc
        
        if inv_account and shrink_account:
            journal = Journal.objects.create(
                tenant=request.tenant, company=request.company,
                journal_number=f"JV-{st.reference}", date=timezone.now().date(),
                description=f"Stocktake Variance {st.reference}", journal_type="ADJUSTMENT",
                status="POSTED", created_by=request.user
            )
            
            if total_variance_value < 0:
                # Shrinkage (Loss)
                JournalLine.objects.create(journal=journal, account=shrink_account, debit=abs(total_variance_value))
                JournalLine.objects.create(journal=journal, account=inv_account, credit=abs(total_variance_value))
            else:
                # Overage (Gain)
                JournalLine.objects.create(journal=journal, account=inv_account, debit=total_variance_value)
                JournalLine.objects.create(journal=journal, account=shrink_account, credit=total_variance_value)

    st.status = "COMPLETED"
    st.approved_by = request.user
    st.completed_at = timezone.now()
    st.save()
    
    return Response({"success": True})
'''

if "def stocktakes_list" not in views_content:
    views_path.write_text(views_content + "\n\n" + stocktake_views, encoding="utf-8")
print("✅ Added StockTake Views and Accounting Logic")

# ============================================================
# 3. Update Inventory URLs
# ============================================================
urls_path = BACKEND_PATH / "inventory" / "urls.py"
urls_content = urls_path.read_text(encoding="utf-8")

if "stocktakes_list" not in urls_content:
    urls_content = urls_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path('stocktakes/', views.stocktakes_list, name='stocktakes_list'),
    path('stocktakes/<int:pk>/', views.stocktake_detail, name='stocktake_detail'),
    path('stocktakes/<int:pk>/scan/', views.stocktake_scan, name='stocktake_scan'),
    path('stocktakes/<int:pk>/submit/', views.stocktake_submit, name='stocktake_submit'),
    path('stocktakes/<int:pk>/approve/', views.stocktake_approve, name='stocktake_approve'),'''
    )
    urls_path.write_text(urls_content, encoding="utf-8")
print("✅ Updated Inventory URLs")

# ============================================================
# 4. Add Frontend HTML Page
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")
if "def stocktake_page" not in web_content:
    web_content += "\n\ndef stocktake_page(request):\n    return render(request, 'pos/stocktake.html')\n"
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/stocktake" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('stocktake', views_web.stocktake_page, name='stocktake_page'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")

html_path = BACKEND_PATH / "templates" / "pos" / "stocktake.html"
html_content = '''
{% extends "pos/base.html" %}
{% block title %}Stock Take{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="stocktakeApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Stock Taking</h1>
      <button @click="createNew()" class="btn-primary" x-show="!activeSt">+ New Stock Take</button>
    </div>

    <!-- List View -->
    <div x-show="!activeSt">
      <div class="card overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr><th class="px-4 py-3">Reference</th><th class="px-4 py-3">Date</th><th class="px-4 py-3">Status</th><th class="px-4 py-3 text-right">Action</th></tr>
          </thead>
          <tbody>
            <template x-for="s in list" :key="s.id">
              <tr class="border-t hover:bg-gray-50">
                <td class="px-4 py-3 font-medium" x-text="s.reference"></td>
                <td class="px-4 py-3 text-gray-500" x-text="s.date"></td>
                <td class="px-4 py-3">
                  <span class="px-2 py-0.5 rounded text-xs font-medium" 
                        :class="{
                          'bg-gray-200 text-gray-700': s.status === 'DRAFT',
                          'bg-yellow-100 text-yellow-700': s.status === 'PENDING',
                          'bg-green-100 text-green-700': s.status === 'COMPLETED'
                        }" x-text="s.status"></span>
                </td>
                <td class="px-4 py-3 text-right">
                  <button @click="openCount(s)" class="text-brand-600 hover:underline">View / Count</button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
        <div x-show="list.length === 0" class="p-8 text-center text-gray-400">No stock takes found.</div>
      </div>
    </div>

    <!-- Active Count View -->
    <div x-show="activeSt" x-cloak>
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold" x-text="'Counting: ' + activeSt?.reference"></h2>
        <button @click="activeSt = null" class="text-sm text-gray-500 hover:underline">Back to List</button>
      </div>

      <!-- Counting Form (Draft only) -->
      <div class="card p-4 mb-6 bg-gray-50" x-show="activeSt?.status === 'DRAFT'">
        <form @submit.prevent="scanItem()" class="flex gap-2">
          <input type="text" x-model="scanForm.barcode" placeholder="Scan Barcode..." class="input-field flex-1" required autofocus>
          <input type="number" step="0.01" x-model="scanForm.counted_qty" placeholder="Qty Counted" class="input-field w-32" required>
          <button type="submit" class="btn-primary">Add Count</button>
        </form>
      </div>

      <div class="card overflow-hidden">
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr><th class="px-4 py-3">Product</th><th class="px-4 py-3 text-center">System Qty</th><th class="px-4 py-3 text-center">Counted</th><th class="px-4 py-3 text-center">Variance</th></tr>
          </thead>
          <tbody>
            <template x-for="i in activeSt?.items || []" :key="i.id">
              <tr class="border-t">
                <td class="px-4 py-3 font-medium" x-text="i.name"></td>
                <td class="px-4 py-3 text-center text-gray-500" x-text="i.system_qty"></td>
                <td class="px-4 py-3 text-center font-bold" x-text="i.counted_qty"></td>
                <td class="px-4 py-3 text-center font-bold" :class="i.variance < 0 ? 'text-red-600' : i.variance > 0 ? 'text-green-600' : 'text-gray-400'" x-text="i.variance"></td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <div class="mt-6 flex gap-2 justify-end">
        <button @click="submitCount()" x-show="activeSt?.status === 'DRAFT'" class="btn-primary" :disabled="activeSt?.items?.length === 0">Submit for Approval</button>
        
        <template x-if="activeSt?.status === 'PENDING' && ['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">
          <button @click="approveCount()" class="btn-primary bg-green-600 hover:bg-green-700">Approve & Adjust Stock</button>
        </template>
        
        <div x-show="activeSt?.status === 'PENDING' && !['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)" class="text-sm text-gray-500 italic py-2">
          Waiting for Manager approval to apply adjustments.
        </div>
      </div>
    </div>

  </div>
</div>

<script>
function stocktakeApp() {
  return {
    list: [], activeSt: null,
    scanForm: { barcode: '', counted_qty: '' },
    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try { this.list = await apiFetch('/inventory/stocktakes/'); } catch(e) { alert(e.message); }
    },
    async createNew() {
      try {
        const res = await apiFetch('/inventory/stocktakes/', { method: 'POST' });
        this.load();
        this.openCount({ id: res.id });
      } catch(e) { alert(e.message); }
    },
    async openCount(st) {
      try { 
        this.activeSt = await apiFetch(`/inventory/stocktakes/${st.id}/`);
        this.scanForm = { barcode: '', counted_qty: '' };
      } catch(e) { alert(e.message); }
    },
    async scanItem() {
      try {
        await apiFetch(`/inventory/stocktakes/${this.activeSt.id}/scan/`, { 
          method: 'POST', body: JSON.stringify(this.scanForm) 
        });
        this.scanForm.barcode = '';
        this.scanForm.counted_qty = '';
        this.openCount(this.activeSt);
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },
    async submitCount() {
      if (!confirm('Submit this count for approval? You will not be able to edit it.')) return;
      try {
        await apiFetch(`/inventory/stocktakes/${this.activeSt.id}/submit/`, { method: 'POST' });
        this.openCount(this.activeSt);
        this.load();
      } catch(e) { alert(e.message); }
    },
    async approveCount() {
      if (!confirm('Approve this count? This will permanently adjust inventory quantities and post accounting entries.')) return;
      try {
        await apiFetch(`/inventory/stocktakes/${this.activeSt.id}/approve/`, { method: 'POST' });
        alert('Stock adjusted successfully!');
        this.openCount(this.activeSt);
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(html_content.strip(), encoding="utf-8")
print("✅ Created Stocktake UI Page")

# Add to Nav
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")
if "href=\"/stocktake\"" not in nav_content:
    nav_content = nav_content.replace(
        '<a href="/products" class="nav-link" x-show="getUser()?.user_type !== \'SALES_AGENT\'">Products</a>',
        '<a href="/products" class="nav-link" x-show="getUser()?.user_type !== \'SALES_AGENT\'">Products</a>\n    <a href="/stocktake" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)">Stock Take</a>'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Stock Take to Sidebar")

# ============================================================
# 5. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "inventory"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)
print("\n🎉 Done! Restart your server.")