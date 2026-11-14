import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add Reservation Models
# ============================================================
models_path = BACKEND_PATH / "sales" / "models.py"
m_content = models_path.read_text(encoding="utf-8")

if "class StockReservation" not in m_content:
    m_content += '''

class StockReservation(models.Model):
    STATUS = [
        ("ACTIVE", "Active (Stock Held)"),
        ("CONVERTED", "Converted to Sale"),
        ("CANCELLED", "Cancelled (Stock Returned)"),
        ("EXPIRED", "Expired"),
    ]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    reservation_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=200, default="Walk-in Customer")
    customer_phone = models.CharField(max_length=20, blank=True)
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    deposit_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="ACTIVE")
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    
    created_by = models.ForeignKey("core.User", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    converted_invoice = models.OneToOneField(Invoice, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.reservation_number

class StockReservationItem(models.Model):
    reservation = models.ForeignKey(StockReservation, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
'''
    models_path.write_text(m_content, encoding="utf-8")
    print("✅ Added StockReservation models.")

# ============================================================
# 2. Add Reservation Views (with Stock Locking Logic)
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

reservation_views = '''
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def reservations_list(request):
    if request.method == "GET":
        qs = StockReservation.objects.filter(tenant=request.tenant, company=request.branch).order_by("-created_at")
        return Response([{
            "id": r.id, "reservation_number": r.reservation_number, 
            "customer": r.customer_name, "phone": r.customer_phone,
            "date": r.created_at.strftime("%Y-%m-%d"),
            "valid_until": r.valid_until.strftime("%Y-%m-%d") if r.valid_until else "N/A",
            "total": float(r.total), "deposit": float(r.deposit_paid), "status": r.status
        } for r in qs[:100]])

    # POST: Create Reservation (Locks Stock)
    data = request.data
    items_data = data.get("items", [])
    if not items_data:
        return Response({"error": "Reservation must have items"}, status=400)

    import datetime
    res_num = f"RES-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

    total_subtotal = Decimal("0")
    total_tax = Decimal("0")
    
    # 1. Validate Stock
    for item in items_data:
        product = Product.objects.get(id=item["product_id"], tenant=request.tenant)
        qty = Decimal(str(item["quantity"]))
        if product.current_stock < qty:
            return Response({"error": f"Not enough stock for {product.name}. Only {product.current_stock} left."}, status=400)

    # 2. Create Reservation
    reservation = StockReservation.objects.create(
        tenant=request.tenant, company=request.branch,
        reservation_number=res_num, 
        customer_id=data.get("customer_id"),
        customer_name=data.get("customer_name", "Walk-in Customer"),
        customer_phone=data.get("customer_phone", ""),
        subtotal=0, tax_total=0, total=0,
        deposit_paid=Decimal(str(data.get("deposit_paid", 0))),
        created_by=request.user,
        valid_until=data.get("valid_until"),
        notes=data.get("notes", "")
    )

    # 3. Create Items & LOCK STOCK
    for item in items_data:
        product = Product.objects.get(id=item["product_id"], tenant=request.tenant)
        qty = Decimal(str(item["quantity"]))
        price = product.selling_price
        line_total = qty * price
        line_tax = line_total * product.tax_rate.rate / 100
        
        total_subtotal += line_total
        total_tax += line_tax
        
        StockReservationItem.objects.create(
            reservation=reservation, product=product, quantity=qty,
            unit_price=price, tax_rate=product.tax_rate.rate, total=line_total
        )
        
        # DEDUCT STOCK IMMEDIATELY
        product.current_stock -= qty
        product.save()

    reservation.subtotal = total_subtotal
    reservation.tax_total = total_tax
    reservation.total = total_subtotal + total_tax
    reservation.save()

    return Response({"success": True, "id": reservation.id, "reservation_number": res_num})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_reservation(request, pk):
    """Cancels reservation and returns stock to the shelf."""
    try:
        r = StockReservation.objects.get(pk=pk, tenant=request.tenant, status="ACTIVE")
    except StockReservation.DoesNotExist:
        return Response({"error": "Reservation not found or already processed"}, status=404)

    # Return stock
    for item in r.items.all():
        product = item.product
        product.current_stock += item.quantity
        product.save()

    r.status = "CANCELLED"
    r.save()

    return Response({"success": True})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def convert_reservation(request, pk):
    """Converts reservation to an invoice. Stock is already deducted."""
    try:
        r = StockReservation.objects.get(pk=pk, tenant=request.tenant, status="ACTIVE")
    except StockReservation.DoesNotExist:
        return Response({"error": "Reservation not found or already processed"}, status=404)

    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "You must open a shift to convert a reservation."}, status=400)

    import datetime
    inv_num = f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-RES"
    
    invoice = Invoice.objects.create(
        invoice_number=inv_num, tenant=request.tenant, company=request.branch,
        shift=shift, cashier=request.user,
        customer_name=r.customer_name, customer_id=r.customer_id,
        subtotal=r.subtotal, tax_total=r.tax_total, total=r.total,
        status="PAID", payment_method="CASH"
    )

    for item in r.items.all():
        InvoiceItem.objects.create(
            invoice=invoice, product=item.product, quantity=item.quantity,
            unit_price=item.unit_price, tax_rate=item.tax_rate,
            tax_amount=(item.total * item.tax_rate / 100), total=item.total,
            zra_item_code=item.product.zra_item_code
        )
        # Note: We do NOT deduct stock here because it was already deducted when the reservation was created.

    r.status = "CONVERTED"
    r.converted_invoice = invoice
    r.save()

    return Response({"success": True, "invoice_id": invoice.id, "invoice_number": invoice.invoice_number})
'''

if "def reservations_list" not in v_content:
    v_content += "\n\n" + reservation_views
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Added Reservation views.")

# Update URLs
urls_path = BACKEND_PATH / "sales" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "reservations_list" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("reservations/", views.reservations_list, name="reservations_list"),\n    path("reservations/<int:pk>/cancel/", views.cancel_reservation, name="cancel_reservation"),\n    path("reservations/<int:pk>/convert/", views.convert_reservation, name="convert_reservation"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
    print("✅ Added Reservation URLs.")

# ============================================================
# 3. Frontend: Route, Nav & UI
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
w_content = views_web.read_text(encoding="utf-8")
if "def reservations_page" not in w_content:
    w_content += "\n\ndef reservations_page(request):\n    return render(request, 'pos/reservations.html')\n"
    views_web.write_text(w_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
wu_content = urls_web.read_text(encoding="utf-8")
if "/reservations" not in wu_content:
    wu_content = wu_content.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('reservations', views_web.reservations_page, name='reservations_page'),"
    )
    urls_web.write_text(wu_content, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
n_content = nav_path.read_text(encoding="utf-8")
if "href=\"/reservations\"" not in n_content:
    n_content = n_content.replace(
        '<a href="/quotations" class="nav-link">',
        '<a href="/quotations" class="nav-link">'
    )
    n_content = n_content.replace(
        '<a href="/invoices" class="nav-link">Invoices</a>',
        '<a href="/invoices" class="nav-link">Invoices</a>\n    <a href="/quotations" class="nav-link"><i data-lucide="file-signature" class="w-4 h-4 mr-3"></i> Quotations</a>\n    <a href="/reservations" class="nav-link"><i data-lucide="lock" class="w-4 h-4 mr-3"></i> Reservations</a>'
    )
    nav_path.write_text(n_content, encoding="utf-8")
print("✅ Added Reservations to Sidebar.")

# Create Reservations UI
html_path = BACKEND_PATH / "templates" / "pos" / "reservations.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Reservations{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="reservationsApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Stock Reservations</h1>
        <p class="text-gray-500 text-sm mt-1">Hold items for customers. Stock is deducted immediately.</p>
      </div>
      <button @click="openModal()" class="btn-primary">+ New Reservation</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Reservation #</th>
            <th class="px-4 py-3">Date</th>
            <th class="px-4 py-3">Customer</th>
            <th class="px-4 py-3">Valid Until</th>
            <th class="px-4 py-3 text-right">Total</th>
            <th class="px-4 py-3 text-right">Deposit</th>
            <th class="px-4 py-3 text-center">Status</th>
            <th class="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="r in reservations" :key="r.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-mono text-xs font-bold text-brand-700" x-text="r.reservation_number"></td>
              <td class="px-4 py-3 text-gray-500" x-text="r.date"></td>
              <td class="px-4 py-3">
                <div class="font-medium text-slate-800" x-text="r.customer"></div>
                <div class="text-xs text-gray-500" x-text="r.phone"></div>
              </td>
              <td class="px-4 py-3 font-medium" :class="r.valid_until === 'N/A' ? 'text-gray-400' : 'text-red-500'" x-text="r.valid_until"></td>
              <td class="px-4 py-3 text-right font-bold" x-text="formatCurrency(r.total)"></td>
              <td class="px-4 py-3 text-right text-green-600" x-text="formatCurrency(r.deposit)"></td>
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-1 rounded text-xs font-bold" 
                      :class="{
                        'bg-green-100 text-green-700': r.status === 'ACTIVE',
                        'bg-gray-100 text-gray-700': r.status === 'CONVERTED',
                        'bg-red-100 text-red-700': r.status === 'CANCELLED'
                      }" x-text="r.status"></span>
              </td>
              <td class="px-4 py-3 text-right space-x-2">
                <template x-if="r.status === 'ACTIVE'">
                  <div>
                    <button @click="convert(r.id)" class="text-brand-600 hover:underline text-xs font-bold mr-2">Sell</button>
                    <button @click="cancel(r.id)" class="text-red-600 hover:underline text-xs font-medium">Cancel</button>
                  </div>
                </template>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="reservations.length === 0" class="p-8 text-center text-gray-400">No active reservations.</div>
    </div>

    <!-- New Reservation Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] p-4" @click.self="showModal = false">
        <div class="bg-white rounded-xl max-w-2xl w-full p-6 max-h-[90vh] flex flex-col">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">New Stock Reservation</h2>
            <button @click="showModal = false" class="text-gray-400 hover:text-red-500 font-bold text-xl">&times;</button>
          </div>

          <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label class="block text-sm mb-1">Customer Name</label>
              <input type="text" x-model="form.customer_name" placeholder="e.g. John Banda" class="input-field" required>
            </div>
            <div>
              <label class="block text-sm mb-1">Phone Number</label>
              <input type="tel" x-model="form.customer_phone" placeholder="e.g. 0971234567" class="input-field">
            </div>
            <div>
              <label class="block text-sm mb-1">Valid Until (Collection Date)</label>
              <input type="date" x-model="form.valid_until" class="input-field">
            </div>
            <div>
              <label class="block text-sm mb-1">Deposit Paid (K)</label>
              <input type="number" step="0.01" x-model="form.deposit_paid" class="input-field" value="0">
            </div>
          </div>

          <div class="flex-1 overflow-y-auto border rounded-lg p-2 bg-gray-50 mb-4">
            <table class="w-full text-sm">
              <thead><tr><th class="text-left pb-2">Product</th><th class="text-right pb-2">Qty</th><th class="text-right pb-2">Stock Available</th></tr></thead>
              <tbody>
                <template x-for="(line, idx) in form.items" :key="idx">
                  <tr>
                    <td class="pr-2">
                      <select x-model="line.product_id" @change="checkStock(line)" class="input-field text-sm py-1" required>
                        <option value="">Select Product...</option>
                        <template x-for="p in products" :key="p.id">
                          <option :value="p.id" x-text="p.name"></option>
                        </template>
                      </select>
                    </td>
                    <td class="pr-2"><input type="number" min="1" x-model="line.quantity" class="input-field text-sm py-1 text-right" required></td>
                    <td class="text-right text-xs font-bold" :class="line.stock_ok ? 'text-green-600' : 'text-red-600'" x-text="line.stock_text"></td>
                  </tr>
                </template>
              </tbody>
            </table>
            <button type="button" @click="form.items.push({product_id:'', quantity:1, stock_ok:true, stock_text:'-'})" class="text-sm text-brand-600 mt-2 hover:underline">+ Add Item</button>
          </div>

          <div class="flex justify-end gap-2 border-t pt-4">
            <button type="button" @click="showModal = false" class="btn-secondary">Cancel</button>
            <button type="button" @click="createReservation()" class="btn-primary" :disabled="saving || !allStockOk">Lock Stock & Create</button>
          </div>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function reservationsApp() {
  return {
    reservations: [], products: [], showModal: false, saving: false,
    form: { customer_name: '', customer_phone: '', valid_until: '', deposit_paid: 0, items: [{product_id:'', quantity:1, stock_ok:true, stock_text:'-'}] },

    get allStockOk() {
      return this.form.items.every(i => i.stock_ok && i.product_id);
    },

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.reservations = await apiFetch('/sales/reservations/');
        this.products = await apiFetch('/inventory/products/');
      } catch(e) { alert(e.message); }
    },

    openModal() {
      this.form = { customer_name: '', customer_phone: '', valid_until: '', deposit_paid: 0, items: [{product_id:'', quantity:1, stock_ok:true, stock_text:'-'}] };
      this.showModal = true;
    },

    checkStock(line) {
      const p = this.products.find(x => x.id == line.product_id);
      if (!p) return;
      if (line.quantity > p.current_stock) {
        line.stock_ok = false;
        line.stock_text = `Only ${p.current_stock} left`;
      } else {
        line.stock_ok = true;
        line.stock_text = `${p.current_stock} available`;
      }
    },

    async createReservation() {
      this.saving = true;
      try {
        await apiFetch('/sales/reservations/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    },

    async convert(id) {
      if (!confirm('Convert to sale? The customer is paying now.')) return;
      try {
        const res = await apiFetch(`/sales/reservations/${id}/convert/`, { method: 'POST' });
        alert(`✅ Converted to Invoice: ${res.invoice_number}`);
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },

    async cancel(id) {
      if (!confirm('Cancel reservation? Stock will be returned to the shelf.')) return;
      try {
        await apiFetch(`/sales/reservations/${id}/cancel/`, { method: 'POST' });
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created reservations.html UI.")

# ============================================================
# 4. Run Migrations
# ============================================================
print("\nRunning migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "sales"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")