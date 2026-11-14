import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add Models
# ============================================================
models_path = BACKEND_PATH / "sales" / "models.py"
m_content = models_path.read_text(encoding="utf-8")

if "class Quotation" not in m_content:
    m_content += '''

class Quotation(models.Model):
    STATUS = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent to Customer"),
        ("CONVERTED", "Converted to Invoice"),
        ("EXPIRED", "Expired"),
        ("CANCELLED", "Cancelled"),
    ]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    quotation_number = models.CharField(max_length=50, unique=True)
    customer = models.ForeignKey("customers.Customer", on_delete=models.SET_NULL, null=True, blank=True)
    customer_name = models.CharField(max_length=200, default="Walk-in Customer")
    
    subtotal = models.DecimalField(max_digits=12, decimal_places=2)
    tax_total = models.DecimalField(max_digits=12, decimal_places=2)
    discount_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    valid_until = models.DateField(null=True, blank=True)
    notes = models.TextField(blank=True)
    created_by = models.ForeignKey("core.User", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)
    converted_invoice = models.OneToOneField(Invoice, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return self.quotation_number

class QuotationItem(models.Model):
    quotation = models.ForeignKey(Quotation, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2)
    total = models.DecimalField(max_digits=12, decimal_places=2)
'''
    models_path.write_text(m_content, encoding="utf-8")
    print("✅ Added Quotation models.")

# ============================================================
# 2. Add Views
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

quotation_views = '''
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def quotations_list(request):
    if request.method == "GET":
        qs = Quotation.objects.filter(tenant=request.tenant, company=request.branch).order_by("-created_at")
        return Response([{
            "id": q.id, "quotation_number": q.quotation_number, 
            "customer": q.customer_name, "date": q.created_at.strftime("%Y-%m-%d"),
            "total": float(q.total), "status": q.status
        } for q in qs[:100]])

    # POST: Create Quotation
    data = request.data
    items_data = data.get("items", [])
    if not items_data:
        return Response({"error": "Quotation must have items"}, status=400)

    import datetime
    q_num = f"QT-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

    total_subtotal = 0
    total_tax = 0
    
    quotation = Quotation.objects.create(
        tenant=request.tenant, company=request.branch,
        quotation_number=q_num, customer_id=data.get("customer_id"),
        customer_name=data.get("customer_name", "Walk-in Customer"),
        subtotal=0, tax_total=0, total=0,
        created_by=request.user,
        valid_until=data.get("valid_until")
    )

    for item in items_data:
        product = Product.objects.get(id=item["product_id"], tenant=request.tenant)
        qty = Decimal(str(item["quantity"]))
        price = product.selling_price
        line_total = qty * price
        line_tax = line_total * product.tax_rate.rate / 100
        
        total_subtotal += line_total
        total_tax += line_tax
        
        QuotationItem.objects.create(
            quotation=quotation, product=product, quantity=qty,
            unit_price=price, tax_rate=product.tax_rate.rate, total=line_total
        )

    quotation.subtotal = total_subtotal
    quotation.tax_total = total_tax
    quotation.total = total_subtotal + total_tax
    quotation.save()

    return Response({"success": True, "id": quotation.id, "quotation_number": q_num})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def convert_quotation(request, pk):
    """Converts a quotation into a paid Invoice and adjusts stock."""
    try:
        q = Quotation.objects.get(pk=pk, tenant=request.tenant, status="DRAFT")
    except Quotation.DoesNotExist:
        return Response({"error": "Quotation not found or already converted"}, status=404)

    # Create the Invoice
    import datetime
    inv_num = f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-CONV"
    
    # We need an open shift to attach the invoice to
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "You must open a shift before converting a quotation."}, status=400)

    invoice = Invoice.objects.create(
        invoice_number=inv_num, tenant=request.tenant, company=request.branch,
        shift=shift, cashier=request.user,
        customer_name=q.customer_name, customer_id=q.customer_id,
        subtotal=q.subtotal, tax_total=q.tax_total, total=q.total,
        status="PAID", payment_method="CASH" # Defaulting to cash for simplicity
    )

    for item in q.items.all():
        InvoiceItem.objects.create(
            invoice=invoice, product=item.product, quantity=item.quantity,
            unit_price=item.unit_price, tax_rate=item.tax_rate,
            tax_amount=(item.total * item.tax_rate / 100), total=item.total,
            zra_item_code=item.product.zra_item_code
        )
        # Deduct stock
        item.product.current_stock -= item.quantity
        item.product.save()

    q.status = "CONVERTED"
    q.converted_invoice = invoice
    q.save()

    return Response({"success": True, "invoice_id": invoice.id, "invoice_number": invoice.invoice_number})
'''

if "def quotations_list" not in v_content:
    v_content += "\n\n" + quotation_views
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Added Quotation views.")

# Update URLs
urls_path = BACKEND_PATH / "sales" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "quotations_list" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("quotations/", views.quotations_list, name="quotations_list"),\n    path("quotations/<int:pk>/convert/", views.convert_quotation, name="convert_quotation"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
    print("✅ Added Quotation URLs.")

# ============================================================
# 3. Frontend: Route & Nav
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
w_content = views_web.read_text(encoding="utf-8")
if "def quotations_page" not in w_content:
    w_content += "\n\ndef quotations_page(request):\n    return render(request, 'pos/quotations.html')\n"
    views_web.write_text(w_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
wu_content = urls_web.read_text(encoding="utf-8")
if "/quotations" not in wu_content:
    wu_content = wu_content.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('quotations', views_web.quotations_page, name='quotations_page'),"
    )
    urls_web.write_text(wu_content, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
n_content = nav_path.read_text(encoding="utf-8")
if "href=\"/quotations\"" not in n_content:
    n_content = n_content.replace(
        '<a href="/invoices" class="nav-link">Invoices</a>',
        '<a href="/invoices" class="nav-link">Invoices</a>\n    <a href="/quotations" class="nav-link"><i data-lucide="file-text" class="w-4 h-4 mr-3"></i> Quotations</a>'
    )
    nav_path.write_text(n_content, encoding="utf-8")
print("✅ Added Quotations to Sidebar.")

# ============================================================
# 4. Frontend: Create Quotations UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "quotations.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Quotations{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="quotationsApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Quotations & Proforma</h1>
        <p class="text-gray-500 text-sm mt-1">Create price quotes for customers and convert them to sales.</p>
      </div>
      <button @click="showModal = true" class="btn-primary">+ New Quotation</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Quotation #</th>
            <th class="px-4 py-3">Date</th>
            <th class="px-4 py-3">Customer</th>
            <th class="px-4 py-3 text-right">Total</th>
            <th class="px-4 py-3 text-center">Status</th>
            <th class="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="q in quotations" :key="q.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-mono text-xs" x-text="q.quotation_number"></td>
              <td class="px-4 py-3 text-gray-500" x-text="q.date"></td>
              <td class="px-4 py-3 font-medium text-slate-800" x-text="q.customer"></td>
              <td class="px-4 py-3 text-right font-bold" x-text="formatCurrency(q.total)"></td>
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded text-xs font-bold" 
                      :class="q.status === 'DRAFT' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'" 
                      x-text="q.status"></span>
              </td>
              <td class="px-4 py-3 text-right">
                <button x-show="q.status === 'DRAFT'" @click="convert(q.id)" class="text-brand-600 hover:underline text-xs font-bold">Convert to Sale</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="quotations.length === 0" class="p-8 text-center text-gray-400">No quotations found.</div>
    </div>

    <!-- New Quotation Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] p-4" @click.self="showModal = false">
        <div class="bg-white rounded-xl max-w-2xl w-full p-6 max-h-[90vh] flex flex-col">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">New Quotation</h2>
            <button @click="showModal = false" class="text-gray-400 hover:text-red-500 font-bold text-xl">&times;</button>
          </div>

          <div class="grid grid-cols-2 gap-4 mb-4">
            <input placeholder="Customer Name (Optional)" x-model="form.customer_name" class="input-field">
            <input type="date" x-model="form.valid_until" class="input-field" title="Valid Until">
          </div>

          <div class="flex-1 overflow-y-auto border rounded-lg p-2 bg-gray-50 mb-4">
            <table class="w-full text-sm">
              <thead><tr><th class="text-left pb-2">Product</th><th class="text-right pb-2">Qty</th><th class="text-right pb-2">Price</th></tr></thead>
              <tbody>
                <template x-for="(line, idx) in form.items" :key="idx">
                  <tr>
                    <td class="pr-2">
                      <select x-model="line.product_id" class="input-field text-sm py-1" required>
                        <option value="">Select Product...</option>
                        <template x-for="p in products" :key="p.id">
                          <option :value="p.id" x-text="p.name + ' (' + formatCurrency(p.selling_price) + ')'"></option>
                        </template>
                      </select>
                    </td>
                    <td class="pr-2"><input type="number" x-model="line.quantity" class="input-field text-sm py-1 text-right" required></td>
                    <td class="text-right text-gray-500 text-xs py-1" x-text="getPrice(line.product_id)"></td>
                  </tr>
                </template>
              </tbody>
            </table>
            <button type="button" @click="form.items.push({product_id:'', quantity:1})" class="text-sm text-brand-600 mt-2 hover:underline">+ Add Line</button>
          </div>

          <div class="flex justify-end gap-2 border-t pt-4">
            <button type="button" @click="showModal = false" class="btn-secondary">Cancel</button>
            <button type="button" @click="createQuotation()" class="btn-primary" :disabled="saving">Create Quote</button>
          </div>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function quotationsApp() {
  return {
    quotations: [], products: [], showModal: false, saving: false,
    form: { customer_name: '', valid_until: '', items: [{product_id:'', quantity:1}] },

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.quotations = await apiFetch('/sales/quotations/');
        this.products = await apiFetch('/inventory/products/');
      } catch(e) { alert(e.message); }
    },

    getPrice(id) {
      const p = this.products.find(x => x.id == id);
      return p ? formatCurrency(p.selling_price) : '-';
    },

    async createQuotation() {
      this.saving = true;
      try {
        await apiFetch('/sales/quotations/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        this.form = { customer_name: '', valid_until: '', items: [{product_id:'', quantity:1}] };
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    },

    async convert(id) {
      if (!confirm('Convert this quotation to a sale? This will deduct stock and generate an invoice.')) return;
      try {
        const res = await apiFetch(`/sales/quotations/${id}/convert/`, { method: 'POST' });
        alert(`✅ Converted to Invoice: ${res.invoice_number}`);
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created quotations.html UI.")

# ============================================================
# 5. Run Migrations
# ============================================================
print("\nRunning migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "sales"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")