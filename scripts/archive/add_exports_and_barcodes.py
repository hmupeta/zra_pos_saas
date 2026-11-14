import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Install Barcode Library
# ============================================================
print("Installing python-barcode...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
subprocess.run([str(python), "-m", "pip", "install", "python-barcode", "pillow", "--quiet"], cwd=BACKEND_PATH)
print("✅ python-barcode installed")

# ============================================================
# 2. Backend Views (CSV Exports & Barcode)
# ============================================================
core_views = BACKEND_PATH / "core" / "views.py"
content = core_views.read_text(encoding="utf-8")

export_views = '''
import csv
from django.http import HttpResponse
from inventory.models import Product
from sales.models import Invoice
from customers.models import Customer

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_products(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="products.csv"'
    writer = csv.writer(response)
    writer.writerow(['Barcode', 'Name', 'Category', 'Cost', 'Selling Price', 'Stock'])
    for p in Product.objects.filter(tenant=request.tenant):
        writer.writerow([p.barcode, p.name, p.category.name, p.unit_cost, p.selling_price, p.current_stock])
    return response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_invoices(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="invoices.csv"'
    writer = csv.writer(response)
    writer.writerow(['Invoice #', 'Date', 'Cashier', 'Customer', 'Total', 'Status'])
    for i in Invoice.objects.filter(tenant=request.tenant):
        writer.writerow([i.invoice_number, i.created_at.strftime("%Y-%m-%d %H:%M"), i.cashier.username, i.customer_name, i.total, i.status])
    return response

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def export_customers(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="customers.csv"'
    writer = csv.writer(response)
    writer.writerow(['Name', 'Phone', 'Email', 'Loyalty Points', 'Total Spent', 'Credit Balance'])
    for c in Customer.objects.filter(tenant=request.tenant):
        writer.writerow([c.full_name, c.phone_number, c.email, c.loyalty_points, c.total_spent, c.account_balance])
    return response

import barcode
from barcode.writer import ImageWriter
from io import BytesIO
import base64

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def generate_barcode_image(request, barcode_num):
    try:
        # Use Code128 format for standard retail barcodes
        CODE128 = barcode.get_barcode_class('code128')
        my_barcode = CODE128(barcode_num, writer=ImageWriter())
        buffer = BytesIO()
        my_barcode.write(buffer)
        
        # Return as base64 image string
        img_str = base64.b64encode(buffer.getvalue()).decode()
        return Response({"success": True, "image": f"data:image/png;base64,{img_str}"})
    except Exception as e:
        return Response({"error": str(e)}, status=400)
'''
core_views.write_text(content + "\n\n" + export_views, encoding="utf-8")

# Update URLs
core_urls = BACKEND_PATH / "core" / "urls.py"
urls_content = core_urls.read_text(encoding="utf-8")
if "export_products" not in urls_content:
    urls_content = urls_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path("export/products/", views.export_products, name="export_products"),
    path("export/invoices/", views.export_invoices, name="export_invoices"),
    path("export/customers/", views.export_customers, name="export_customers"),
    path("barcode/<str:barcode_num>/", views.generate_barcode_image, name="generate_barcode"),'''
    )
    core_urls.write_text(urls_content, encoding="utf-8")
print("✅ Added CSV Export & Barcode API endpoints")

# ============================================================
# 3. Add Frontend Route & Nav for Barcodes
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")
if "def barcodes_page" not in web_content:
    web_content += "\n\ndef barcodes_page(request):\n    return render(request, 'pos/barcodes.html')\n"
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/barcodes" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('barcodes', views_web.barcodes_page, name='barcodes_page'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")
if "href=\"/barcodes\"" not in nav_content:
    nav_content = nav_content.replace(
        '<a href="/categories" class="nav-link"',
        '<a href="/barcodes" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)"><i data-lucide="printer" class="w-4 h-4 mr-3"></i> Barcode Gen</a>\n    <a href="/categories" class="nav-link"'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Barcode Generator to Sidebar")

# ============================================================
# 4. Add Export Buttons to Existing UI Pages
# ============================================================
# A. Products UI
products_path = BACKEND_PATH / "templates" / "pos" / "products.html"
p_content = products_path.read_text(encoding="utf-8")
p_content = p_content.replace(
    '<div class="flex gap-2">\n        <button @click="openReceiveModal(null)" class="btn-secondary">+ Receive Stock</button>',
    '<div class="flex gap-2">\n        <a href="/api/auth/export/products/" class="btn-secondary">Export CSV</a>\n        <button @click="openReceiveModal(null)" class="btn-secondary">+ Receive Stock</button>'
)
products_path.write_text(p_content, encoding="utf-8")

# B. Invoices UI
invoices_path = BACKEND_PATH / "templates" / "pos" / "invoices.html"
i_content = invoices_path.read_text(encoding="utf-8")
i_content = i_content.replace(
    '<h1 class="text-2xl font-bold mb-6">Invoices</h1>',
    '<div class="flex justify-between items-center mb-6">\n      <h1 class="text-2xl font-bold">Invoices</h1>\n      <a href="/api/auth/export/invoices/" class="btn-secondary text-sm">Export CSV</a>\n    </div>'
)
invoices_path.write_text(i_content, encoding="utf-8")

# C. Customers UI
customers_path = BACKEND_PATH / "templates" / "pos" / "customers.html"
c_content = customers_path.read_text(encoding="utf-8")
c_content = c_content.replace(
    '<h1 class="text-2xl font-bold">Customer Directory</h1>',
    '<div class="flex gap-2">\n        <a href="/api/auth/export/customers/" class="btn-secondary text-sm">Export CSV</a>\n        <button @click="showModal = true" class="btn-primary">+ Add Customer</button>\n      </div>'
).replace(
    '<button @click="showModal = true" class="btn-primary">+ Add Customer</button>\n      </div>\n    </div>',
    '</div>\n    </div>'
)
# Fix the header layout
c_content = c_content.replace(
    '<div class="flex justify-between items-center mb-6">\n      <div class="flex gap-2">',
    '<div class="flex justify-between items-center mb-6">\n      <h1 class="text-2xl font-bold">Customer Directory</h1>\n      <div class="flex gap-2">'
)
c_content = c_content.replace(
    '<h1 class="text-2xl font-bold">Customer Directory</h1>\n      <div class="flex gap-2">\n        <a href="/api/auth/export/customers/"',
    '<div class="flex gap-2">\n        <a href="/api/auth/export/customers/"'
)
# Actually, let's just replace the whole header block to be safe
import re
c_content = re.sub(r'<div class="flex justify-between items-center mb-6">.*?</div>\s*</div>', 
'''<div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Customer Directory</h1>
      <div class="flex gap-2">
        <a href="/api/auth/export/customers/" class="btn-secondary text-sm">Export CSV</a>
        <button @click="showModal = true" class="btn-primary">+ Add Customer</button>
      </div>
    </div>''', c_content, count=1, flags=re.DOTALL)

customers_path.write_text(c_content, encoding="utf-8")
print("✅ Added Export CSV buttons to Products, Invoices, and Customers")

# ============================================================
# 5. Create Barcode Generator UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "barcodes.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Barcode Generator{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="barcodeApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold">Barcode Label Generator</h1>
        <p class="text-gray-500 text-sm mt-1">Select products below to generate and print barcode labels.</p>
      </div>
      <button @click="printLabels()" class="btn-primary flex items-center gap-2" :disabled="Object.keys(selected).length === 0">
        <i data-lucide="printer" class="w-4 h-4"></i> Print Selected Labels
      </button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3 w-12">
              <input type="checkbox" @change="toggleAll($event)" class="rounded">
            </th>
            <th class="px-4 py-3">Product</th>
            <th class="px-4 py-3">Barcode</th>
            <th class="px-4 py-3">Preview</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="p in products" :key="p.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3">
                <input type="checkbox" :value="p.id" x-model="selected[p.id]" class="rounded">
              </td>
              <td class="px-4 py-3 font-medium" x-text="p.name"></td>
              <td class="px-4 py-3 font-mono text-xs" x-text="p.barcode"></td>
              <td class="px-4 py-3">
                <button @click="previewBarcode(p.barcode)" class="text-xs text-brand-600 hover:underline">View Barcode</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Preview Modal -->
    <template x-if="previewImg">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-sm w-full p-6 text-center">
          <h2 class="text-lg font-bold mb-4">Barcode Preview</h2>
          <img :src="previewImg" class="mx-auto border p-4 bg-white rounded">
          <button @click="previewImg = null" class="btn-secondary w-full mt-4">Close</button>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function barcodeApp() {
  return {
    products: [], selected: {}, previewImg: null,
    
    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.products = await apiFetch('/inventory/products/');
      } catch(e) { alert(e.message); }
    },

    toggleAll(e) {
      if (e.target.checked) {
        this.products.forEach(p => this.selected[p.id] = true);
      } else {
        this.selected = {};
      }
    },

    async previewBarcode(barcode) {
      try {
        const res = await apiFetch(`/auth/barcode/${barcode}/`);
        this.previewImg = res.image;
      } catch(e) { alert(e.message); }
    },

    async printLabels() {
      const items = this.products.filter(p => this.selected[p.id]);
      if (items.length === 0) return;

      let win = window.open('', '_blank');
      win.document.write('<html><head><title>Print Barcodes</title>');
      win.document.write('<style>');
      win.document.write('body { font-family: Arial; display: flex; flex-wrap: wrap; gap: 20px; padding: 20px; }');
      win.document.write('.label { width: 200px; border: 1px dashed #ccc; padding: 10px; text-align: center; }');
      win.document.write('.label img { max-width: 100%; height: auto; }');
      win.document.write('.label p { margin: 5px 0; font-size: 12px; font-weight: bold; }');
      win.document.write('</style></head><body>');

      for (let p of items) {
        try {
          const res = await apiFetch(`/auth/barcode/${p.barcode}/`);
          win.document.write(`<div class="label">`);
          win.document.write(`<p>${p.name}</p>`);
          win.document.write(`<img src="${res.image}">`);
          win.document.write(`</div>`);
        } catch(e) { console.error(e); }
      }

      win.document.write('</body></html>');
      win.document.close();
      setTimeout(() => win.print(), 500);
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created Barcode Generator UI")

print("\n🎉 Done! Restart the server.")