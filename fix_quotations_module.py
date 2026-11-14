import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Backend: Add Detail/Edit/Delete View
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

detail_view = '''
@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def quotation_detail(request, pk):
    try:
        q = Quotation.objects.get(pk=pk, tenant=request.tenant)
    except Quotation.DoesNotExist:
        return Response({"error": "Quotation not found"}, status=404)

    if request.method == "GET":
        return Response({
            "id": q.id,
            "quotation_number": q.quotation_number,
            "customer": q.customer_name,
            "customer_id": q.customer_id,
            "valid_until": q.valid_until.strftime("%Y-%m-%d") if q.valid_until else "",
            "status": q.status,
            "notes": q.notes,
            "items": [{
                "id": i.id,
                "product_id": i.product_id,
                "product_name": i.product.name,
                "quantity": float(i.quantity),
                "unit_price": float(i.unit_price),
                "total": float(i.total)
            } for i in q.items.all()]
        })

    elif request.method == "PUT":
        if q.status != "DRAFT":
            return Response({"error": "Only draft quotations can be edited"}, status=400)

        data = request.data
        items_data = data.get("items", [])
        if not items_data:
            return Response({"error": "Quotation must have items"}, status=400)

        total_subtotal = Decimal("0")
        total_tax = Decimal("0")

        # Clear existing items
        q.items.all().delete()

        for item in items_data:
            product = Product.objects.get(id=item["product_id"], tenant=request.tenant)
            qty = Decimal(str(item["quantity"]))
            price = product.selling_price
            line_total = qty * price
            line_tax = line_total * product.tax_rate.rate / 100

            total_subtotal += line_total
            total_tax += line_tax

            QuotationItem.objects.create(
                quotation=q, product=product, quantity=qty,
                unit_price=price, tax_rate=product.tax_rate.rate, total=line_total
            )

        q.customer_id = data.get("customer_id") or None
        q.customer_name = data.get("customer_name", "Walk-in Customer")
        q.valid_until = data.get("valid_until") or None
        q.subtotal = total_subtotal
        q.tax_total = total_tax
        q.total = total_subtotal + total_tax
        q.save()

        return Response({"success": True})

    elif request.method == "DELETE":
        if q.status != "DRAFT":
            return Response({"error": "Only draft quotations can be deleted"}, status=400)
        q.delete()
        return Response({"success": True})
'''

if "def quotation_detail" not in v_content:
    v_content += "\n\n" + detail_view
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Added quotation_detail view.")

# Update URLs
urls_path = BACKEND_PATH / "sales" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "quotation_detail" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("quotations/<int:pk>/", views.quotation_detail, name="quotation_detail"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
    print("✅ Added quotation_detail URL.")

# ============================================================
# 2. Frontend: Rebuild quotations.html completely
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "quotations.html"
full_html = '''
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
      <button @click="openNewModal()" class="btn-primary">+ New Quotation</button>
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
              <td class="px-4 py-3 font-mono text-xs font-bold text-brand-700" x-text="q.quotation_number"></td>
              <td class="px-4 py-3 text-gray-500" x-text="q.date"></td>
              <td class="px-4 py-3 font-medium text-slate-800" x-text="q.customer"></td>
              <td class="px-4 py-3 text-right font-bold" x-text="formatCurrency(q.total)"></td>
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded text-xs font-bold" 
                      :class="q.status === 'DRAFT' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'" 
                      x-text="q.status"></span>
              </td>
              <td class="px-4 py-3 text-right space-x-2">
                <button @click="viewQuote(q.id)" class="text-blue-600 hover:underline text-xs font-medium">View</button>
                <template x-if="q.status === 'DRAFT'">
                  <div class="inline-block">
                    <button @click="editQuote(q.id)" class="text-orange-500 hover:underline text-xs font-medium mx-1">Edit</button>
                    <button @click="deleteQuote(q.id)" class="text-red-500 hover:underline text-xs font-medium mx-1">Delete</button>
                    <button @click="convert(q.id)" class="text-brand-600 hover:underline text-xs font-bold mx-1">Convert</button>
                  </div>
                </template>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="quotations.length === 0" class="p-8 text-center text-gray-400">No quotations found.</div>
    </div>

    <!-- Create/Edit Quotation Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] p-4" @click.self="showModal = false">
        <div class="bg-white rounded-xl max-w-2xl w-full p-6 max-h-[90vh] flex flex-col">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold" x-text="form.id ? 'Edit Quotation' : 'New Quotation'"></h2>
            <button @click="showModal = false" class="text-gray-400 hover:text-red-500 font-bold text-xl">&times;</button>
          </div>

          <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label class="block text-sm mb-1">Customer</label>
              <div class="flex gap-2">
                <select x-model="form.customer_id" @change="selectCustomer($event)" class="input-field flex-1">
                  <option value="">Walk-in Customer</option>
                  <template x-for="c in customers" :key="c.id">
                    <option :value="c.id" x-text="c.name + ' (' + c.phone + ')'"></option>
                  </template>
                </select>
                <button type="button" @click.prevent="showCustomerModal = true" class="btn-secondary px-3" title="Add New Customer">
                  <i data-lucide="plus" class="w-4 h-4"></i>
                </button>
              </div>
            </div>
            <div>
              <label class="block text-sm mb-1">Valid Until</label>
              <input type="date" x-model="form.valid_until" class="input-field">
            </div>
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
                    <td class="pr-2"><input type="number" min="1" x-model="line.quantity" class="input-field text-sm py-1 text-right" required></td>
                    <td class="text-right text-gray-500 text-xs py-1" x-text="getPrice(line.product_id)"></td>
                  </tr>
                </template>
              </tbody>
            </table>
            <button type="button" @click="form.items.push({product_id:'', quantity:1})" class="text-sm text-brand-600 mt-2 hover:underline">+ Add Line</button>
          </div>

          <div class="flex justify-end gap-2 border-t pt-4">
            <button type="button" @click="showModal = false" class="btn-secondary">Cancel</button>
            <button type="button" @click="saveQuotation()" class="btn-primary" :disabled="saving">
              <span x-text="saving ? 'Saving...' : (form.id ? 'Update Quote' : 'Create Quote')"></span>
            </button>
          </div>
        </div>
      </div>
    </template>

    <!-- View Quotation Modal -->
    <template x-if="viewModal">
      <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[9999] p-4 backdrop-blur-sm" @click.self="viewModal = null">
        <div class="bg-white rounded-xl max-w-2xl w-full p-6 shadow-2xl max-h-[90vh] flex flex-col">
          <div class="flex justify-between items-center mb-4 border-b pb-4">
            <div>
              <h2 class="text-2xl font-bold text-slate-800">Quotation</h2>
              <p class="text-brand-600 font-mono text-sm" x-text="viewModal.quotation_number"></p>
            </div>
            <div class="text-right">
              <div class="text-sm text-gray-500">Date: <span x-text="new Date().toLocaleDateString()"></span></div>
              <div class="text-sm text-gray-500">Valid Until: <span x-text="viewModal.valid_until || 'N/A'"></span></div>
            </div>
          </div>

          <div class="mb-6">
            <p class="text-sm text-gray-500">Prepared For:</p>
            <p class="font-bold text-lg" x-text="viewModal.customer || 'Walk-in Customer'"></p>
          </div>

          <div class="flex-1 overflow-y-auto border rounded-lg mb-4">
            <table class="w-full text-sm">
              <thead class="bg-gray-50 text-left"><tr><th class="p-3">Product</th><th class="p-3 text-right">Qty</th><th class="p-3 text-right">Price</th><th class="p-3 text-right">Total</th></tr></thead>
              <tbody>
                <template x-for="item in viewModal.items" :key="item.id">
                  <tr class="border-t">
                    <td class="p-3" x-text="item.product_name"></td>
                    <td class="p-3 text-right" x-text="item.quantity"></td>
                    <td class="p-3 text-right" x-text="formatCurrency(item.unit_price)"></td>
                    <td class="p-3 text-right font-bold" x-text="formatCurrency(item.total)"></td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>

          <div class="flex justify-end gap-2 border-t pt-4">
            <button @click="printQuote()" class="btn-secondary flex items-center gap-2">
              <i data-lucide="printer" class="w-4 h-4"></i> Print
            </button>
            <button @click="viewModal = null" class="btn-primary">Close</button>
          </div>
        </div>
      </div>
    </template>

    <!-- Quick Add Customer Modal -->
    <template x-if="showCustomerModal">
      <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[10000] p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl max-w-sm w-full p-6 shadow-2xl">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">New Customer</h2>
            <button @click="showCustomerModal = false" class="text-gray-400 hover:text-red-500 font-bold text-xl">&times;</button>
          </div>
          <form @submit.prevent="createNewCustomer()" class="space-y-3">
            <input type="text" x-model="newCust.phone_number" placeholder="Phone Number" class="input-field" required>
            <input type="text" x-model="newCust.first_name" placeholder="First Name" class="input-field" required>
            <input type="text" x-model="newCust.last_name" placeholder="Last Name (Optional)" class="input-field">
            <div class="flex gap-2 mt-4">
              <button type="button" @click="showCustomerModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1" :disabled="savingCustomer">
                <span x-show="!savingCustomer">Save Customer</span>
                <span x-show="savingCustomer">Saving...</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>

<script>
function quotationsApp() {
  return {
    quotations: [], products: [], customers: [], 
    showModal: false, showCustomerModal: false, viewModal: null, 
    saving: false, savingCustomer: false,
    form: { id: null, customer_id: '', customer_name: '', valid_until: '', items: [{product_id:'', quantity:1}] },
    newCust: { first_name: '', last_name: '', phone_number: '' },

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.quotations = await apiFetch('/sales/quotations/');
        this.products = await apiFetch('/inventory/products/');
        this.customers = await apiFetch('/customers/');
        setTimeout(() => { lucide.createIcons(); }, 100);
      } catch(e) { alert(e.message); }
    },

    getPrice(id) {
      const p = this.products.find(x => x.id == id);
      return p ? formatCurrency(p.selling_price) : '-';
    },

    selectCustomer(event) {
      const id = event.target.value;
      if (!id) {
        this.form.customer_name = 'Walk-in Customer';
        return;
      }
      const c = this.customers.find(x => x.id == id);
      if (c) this.form.customer_name = c.name;
    },

    async createNewCustomer() {
      this.savingCustomer = true;
      try {
        const res = await apiFetch('/customers/', { method: 'POST', body: JSON.stringify(this.newCust) });
        this.customers = await apiFetch('/customers/');
        this.form.customer_id = res.id;
        this.form.customer_name = res.name;
        this.showCustomerModal = false;
        this.newCust = { first_name: '', last_name: '', phone_number: '' };
      } catch (e) { alert(e.response?.data?.error || e.message); }
      finally { this.savingCustomer = false; }
    },

    openNewModal() {
      this.form = { id: null, customer_id: '', customer_name: '', valid_until: '', items: [{product_id:'', quantity:1}] };
      this.showModal = true;
    },

    async saveQuotation() {
      this.saving = true;
      try {
        const method = this.form.id ? 'PUT' : 'POST';
        const url = this.form.id ? `/sales/quotations/${this.form.id}/` : '/sales/quotations/';
        await apiFetch(url, { method: method, body: JSON.stringify(this.form) });
        this.showModal = false;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    },

    async viewQuote(id) {
      try {
        this.viewModal = await apiFetch(`/sales/quotations/${id}/`);
        setTimeout(() => { lucide.createIcons(); }, 50);
      } catch(e) { alert(e.message); }
    },

    async editQuote(id) {
      try {
        const q = await apiFetch(`/sales/quotations/${id}/`);
        this.form = {
          id: q.id, customer_id: q.customer_id || '', 
          customer_name: q.customer, valid_until: q.valid_until,
          items: q.items.map(i => ({ product_id: i.product_id, quantity: i.quantity }))
        };
        this.showModal = true;
      } catch(e) { alert(e.message); }
    },

    async deleteQuote(id) {
      if (!confirm('Delete this quotation? This cannot be undone.')) return;
      try {
        await apiFetch(`/sales/quotations/${id}/`, { method: 'DELETE' });
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },

    async convert(id) {
      if (!confirm('Convert to sale? This will deduct stock and generate an invoice.')) return;
      try {
        const res = await apiFetch(`/sales/quotations/${id}/convert/`, { method: 'POST' });
        alert(`✅ Converted to Invoice: ${res.invoice_number}`);
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },

    printQuote() {
      if (!this.viewModal) return;
      const q = this.viewModal;
      let itemsHtml = q.items.map(i => `
        <tr>
          <td>${i.product_name}</td>
          <td style="text-align:right">${i.quantity}</td>
          <td style="text-align:right">K${i.unit_price.toFixed(2)}</td>
          <td style="text-align:right">K${i.total.toFixed(2)}</td>
        </tr>
      `).join('');
      
      let total = q.items.reduce((s, i) => s + i.total, 0);

      const win = window.open('', '_blank');
      win.document.write(`
        <html><head><title>Quotation ${q.quotation_number}</title>
        <style>
          body { font-family: Arial, sans-serif; padding: 40px; color: #333; }
          .header { text-align: center; border-bottom: 2px solid #4f46e5; padding-bottom: 20px; margin-bottom: 30px; }
          .company-name { font-size: 24px; font-weight: bold; color: #4f46e5; margin: 0; }
          .details { display: flex; justify-content: space-between; margin-bottom: 30px; }
          table { width: 100%; border-collapse: collapse; margin-bottom: 20px; }
          th, td { padding: 10px; border-bottom: 1px solid #ddd; }
          th { background: #f9fafb; text-align: left; }
          .total { font-weight: bold; font-size: 20px; text-align: right; margin-top: 20px; }
        </style></head><body>
        <div class="header">
          <h1 class="company-name">Nimbus POS Store</h1>
          <p>123 Cairo Road, Lusaka | TPIN: 1000000000</p>
        </div>
        <div class="details">
          <div>
            <strong>Quotation To:</strong><br>
            ${q.customer || 'Walk-in Customer'}
          </div>
          <div style="text-align:right">
            <strong>Quote #:</strong> ${q.quotation_number}<br>
            <strong>Valid Until:</strong> ${q.valid_until || 'N/A'}
          </div>
        </div>
        <table>
          <thead><tr><th>Item</th><th style="text-align:right">Qty</th><th style="text-align:right">Price</th><th style="text-align:right">Total</th></tr></thead>
          <tbody>${itemsHtml}</tbody>
        </table>
        <div class="total">Total Estimate: K${total.toFixed(2)}</div>
        <p style="margin-top:50px; font-size:12px; color:#666; text-align:center">This is a quotation and not a valid tax invoice.</p>
        <script>window.onload=()=>{window.print();setTimeout(()=>window.close(),100);}<\/script>
        </body></html>
      `);
      win.document.close();
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(full_html.strip(), encoding="utf-8")
print("✅ Completely rebuilt quotations.html with View, Edit, Delete, Print, and New Customer Modal.")

# ============================================================
# 3. Run Migrations (just in case)
# ============================================================
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server and do a HARD REFRESH (Ctrl + Shift + R).")