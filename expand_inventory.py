import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def get_python():
    venv = BACKEND_PATH / "venv"
    if platform.system() == "Windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"

# ============================================================
# 1. Update Models (Add Image field)
# ============================================================
models_path = BACKEND_PATH / "inventory" / "models.py"
models_content = models_path.read_text(encoding="utf-8")

if "image = models.ImageField" not in models_content:
    # We insert the image field right after the description
    models_content = models_content.replace(
        "description = models.TextField(blank=True)",
        "description = models.TextField(blank=True)\n    image = models.ImageField(upload_to='products/', null=True, blank=True)"
    )
    models_path.write_text(models_content, encoding="utf-8")
print("✅ Added image field to Product model")

# ============================================================
# 2. Update Views (Handle Multipart, Add Stock Receiving, Serialize Image)
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
new_views = '''
from django.db.models import F
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Product, Category, TaxRate, StockMovement
from .serializers import ProductSerializer, CategorySerializer, TaxRateSerializer
from decimal import Decimal
import uuid

@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def products_list(request):
    if request.method == 'GET':
        search = request.query_params.get('search', '')
        products = Product.objects.filter(tenant=request.tenant, company=request.branch, is_active=True)
        if search:
            products = products.filter(name__icontains=search) | products.filter(barcode__icontains=search)
            
        data = []
        for p in products:
            data.append({
                "id": p.id,
                "barcode": p.barcode,
                "name": p.name,
                "selling_price": float(p.selling_price),
                "unit_cost": float(p.unit_cost),
                "current_stock": float(p.current_stock),
                "tax_rate": float(p.tax_rate.rate),
                "category_name": p.category.name,
                "image_url": p.image.url if p.image else None,
            })
        return Response(data)
        
    # POST: Create Product (Multipart/FormData)
    data = request.data
    try:
        barcode = data.get("barcode") or str(uuid.uuid4().hex[:10]).upper()
        
        product = Product.objects.create(
            tenant=request.tenant,
            company=request.branch,
            barcode=barcode,
            name=data.get("name"),
            description=data.get("description", ""),
            category_id=data.get("category_id"),
            tax_rate_id=data.get("tax_rate_id"),
            unit_cost=Decimal(str(data.get("unit_cost", 0))),
            selling_price=Decimal(str(data.get("selling_price", 0))),
            current_stock=Decimal(str(data.get("current_stock", 0))),
            reorder_level=Decimal(str(data.get("reorder_level", 10))),
            zra_item_code=data.get("zra_item_code", ""),
            image=request.FILES.get("image") # Handle File Upload
        )
        return Response({"success": True, "id": product.id}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def receive_stock(request):
    """Adds inventory to an existing product."""
    try:
        product_id = request.data.get("product_id")
        qty = Decimal(str(request.data.get("quantity", 0)))
        new_cost = Decimal(str(request.data.get("unit_cost", 0)))
        supplier_ref = request.data.get("reference", "")

        product = Product.objects.get(pk=product_id, tenant=request.tenant)

        # Update stock and cost
        product.current_stock += qty
        if new_cost > 0:
            product.unit_cost = new_cost
        product.save()

        # Record the movement
        StockMovement.objects.create(
            product=product,
            quantity=qty,
            movement_type='IN',
            reference=supplier_ref,
            created_by=request.user
        )

        return Response({"success": True, "new_stock": float(product.current_stock)})
    except Product.DoesNotExist:
        return Response({"error": "Product not found"}, status=404)
    except Exception as e:
        return Response({"error": str(e)}, status=400)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def product_by_barcode(request, barcode):
    try:
        product = Product.objects.get(barcode=barcode, tenant=request.tenant, is_active=True)
        return Response(ProductSerializer(product).data)
    except Product.DoesNotExist:
        return Response({'error': 'Product not found'}, status=404)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def categories_list(request):
    cats = Category.objects.filter(tenant=request.tenant, is_active=True)
    return Response([{"id": c.id, "name": c.name} for c in cats])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def tax_rates_list(request):
    taxes = TaxRate.objects.filter(tenant=request.tenant)
    return Response([{"id": t.id, "name": t.name, "rate": float(t.rate)} for t in taxes])

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def low_stock_products(request):
    products = Product.objects.filter(tenant=request.tenant, current_stock__lte=F('reorder_level'), is_active=True)
    return Response(ProductSerializer(products, many=True).data)
'''
views_path.write_text(new_views.strip(), encoding="utf-8")
print("✅ Rebuilt inventory/views.py with Image Upload and Stock Receive logic")

# ============================================================
# 3. Update URLs
# ============================================================
urls_path = BACKEND_PATH / "inventory" / "urls.py"
new_urls = '''
from django.urls import path
from . import views

urlpatterns = [
    path('products/', views.products_list, name='products_list'),
    path('products/receive/', views.receive_stock, name='receive_stock'),
    path('products/barcode/<str:barcode>/', views.product_by_barcode, name='product_by_barcode'),
    path('categories/', views.categories_list, name='categories'),
    path('tax-rates/', views.tax_rates_list, name='tax_rates'),
    path('low-stock/', views.low_stock_products, name='low_stock'),
]
'''
urls_path.write_text(new_urls.strip(), encoding="utf-8")
print("✅ Updated inventory/urls.py")

# ============================================================
# 4. Update api.js to handle FormData automatically
# ============================================================
api_js = BACKEND_PATH / "static" / "pos" / "api.js"
js_content = api_js.read_text(encoding="utf-8")

old_header = "const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };"
new_header = """
  const isFormData = options.body instanceof FormData;
  const headers = { 
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }), 
    ...(options.headers || {}) 
  };
"""
js_content = js_content.replace(old_header, new_header)
api_js.write_text(js_content, encoding="utf-8")
print("✅ Updated api.js to auto-detect FormData")

# ============================================================
# 5. Rebuild Products HTML (Images, Cost, Receive Stock)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Products{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="productsPage()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Products & Inventory</h1>
      <div class="flex gap-2">
        <button @click="openReceiveModal(null)" class="btn-secondary">+ Receive Stock</button>
        <button @click="showModal = true" class="btn-primary">+ New Product</button>
      </div>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Product</th>
            <th class="px-4 py-3">Barcode</th>
            <th class="px-4 py-3 text-right">Cost</th>
            <th class="px-4 py-3 text-right">Selling</th>
            <th class="px-4 py-3 text-center">Stock</th>
            <th class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="p in filtered" :key="p.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 bg-gray-100 rounded overflow-hidden flex-shrink-0">
                    <template x-if="p.image_url">
                      <img :src="p.image_url" class="w-full h-full object-cover">
                    </template>
                    <template x-if="!p.image_url">
                      <div class="w-full h-full flex items-center justify-center text-xs text-gray-400">No Img</div>
                    </template>
                  </div>
                  <div>
                    <div class="font-medium" x-text="p.name"></div>
                    <div class="text-xs text-gray-500" x-text="p.category_name"></div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 font-mono text-xs" x-text="p.barcode"></td>
              <td class="px-4 py-3 text-right text-gray-500" x-text="formatCurrency(p.unit_cost)"></td>
              <td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(p.selling_price)"></td>
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded text-xs" :class="p.current_stock <= 10 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'" x-text="p.current_stock"></span>
              </td>
              <td class="px-4 py-3 text-right">
                <button @click="openReceiveModal(p)" class="text-xs text-brand-600 hover:underline">Add Stock</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="filtered.length === 0" class="p-8 text-center text-gray-400">No products found</div>
    </div>

    <!-- New Product Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-lg w-full p-6">
          <h2 class="text-xl font-bold mb-4">New Product</h2>
          <form @submit.prevent="create()" class="space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <input placeholder="Barcode (leave blank to auto-gen)" x-model="form.barcode" class="input-field">
              <input placeholder="Product Name" x-model="form.name" class="input-field" required>
            </div>
            
            <div class="grid grid-cols-2 gap-3">
              <select x-model="form.category_id" class="input-field" required>
                <option value="">Select Category</option>
                <template x-for="c in categories" :key="c.id">
                  <option :value="c.id" x-text="c.name"></option>
                </template>
              </select>
              <select x-model="form.tax_rate_id" class="input-field" required>
                <option value="">Select Tax</option>
                <template x-for="t in taxes" :key="t.id">
                  <option :value="t.id" x-text="t.name + ' (' + t.rate + '%)'"></option>
                </template>
              </select>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-500 mb-1">Cost Price</label>
                <input type="number" step="0.01" x-model="form.unit_cost" class="input-field" required>
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">Selling Price</label>
                <input type="number" step="0.01" x-model="form.selling_price" class="input-field" required>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-500 mb-1">Opening Stock</label>
                <input type="number" step="0.01" x-model="form.current_stock" class="input-field">
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">Reorder Level</label>
                <input type="number" step="0.01" x-model="form.reorder_level" class="input-field">
              </div>
            </div>

            <div>
              <label class="block text-xs text-gray-500 mb-1">Product Image</label>
              <input type="file" @change="handleFile" accept="image/*" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700">
            </div>

            <div class="flex gap-2 mt-4">
              <button type="button" @click="showModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1" :disabled="saving">Save Product</button>
            </div>
          </form>
        </div>
      </div>
    </template>

    <!-- Receive Stock Modal -->
    <template x-if="receiveModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4">Receive Inventory</h2>
          <form @submit.prevent="receiveStock()" class="space-y-3">
            <div>
              <label class="block text-sm font-medium mb-1">Product</label>
              <select x-model="receiveForm.product_id" @change="onReceiveSelect" class="input-field" required>
                <option value="">Select product...</option>
                <template x-for="p in products" :key="p.id">
                  <option :value="p.id" x-text="p.name + ' (Stock: ' + p.current_stock + ')'"></option>
                </template>
              </select>
            </div>
            
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-sm font-medium mb-1">Qty Received</label>
                <input type="number" step="0.01" x-model="receiveForm.quantity" class="input-field" required>
              </div>
              <div>
                <label class="block text-sm font-medium mb-1">Unit Cost</label>
                <input type="number" step="0.01" x-model="receiveForm.unit_cost" class="input-field" required>
              </div>
            </div>
            
            <div>
              <label class="block text-sm font-medium mb-1">Supplier / Reference (Optional)</label>
              <input type="text" x-model="receiveForm.reference" class="input-field" placeholder="e.g. Invoice #1234">
            </div>

            <div class="flex gap-2 mt-4">
              <button type="button" @click="receiveModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1" :disabled="saving">Add to Stock</button>
            </div>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>

<script>
function productsPage() {
  return {
    products: [], categories: [], taxes: [], search: '',
    showModal: false, receiveModal: false, saving: false,
    
    // New Product Form
    form: { barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', current_stock: 0, reorder_level: 10 },
    imageFile: null,

    // Receive Stock Form
    receiveForm: { product_id: '', quantity: '', unit_cost: '', reference: '' },

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.products = await apiFetch('/inventory/products/');
        this.categories = await apiFetch('/inventory/categories/');
        this.taxes = await apiFetch('/inventory/tax-rates/');
      } catch(e) { alert(e.message); }
    },

    get filtered() {
      const q = this.search.toLowerCase();
      return q ? this.products.filter(p => p.name.toLowerCase().includes(q) || p.barcode.includes(q)) : this.products;
    },

    handleFile(e) {
      if (e.target.files.length > 0) this.imageFile = e.target.files[0];
    },

    async create() {
      this.saving = true;
      try {
        const fd = new FormData();
        Object.keys(this.form).forEach(k => fd.append(k, this.form[k]));
        if (this.imageFile) fd.append('image', this.imageFile);

        await apiFetch('/inventory/products/', { method: 'POST', body: fd });
        
        this.showModal = false;
        this.form = { barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', current_stock: 0, reorder_level: 10 };
        this.imageFile = null;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    },

    openReceiveModal(product) {
      if (product) {
        this.receiveForm = { product_id: product.id, quantity: '', unit_cost: product.unit_cost, reference: '' };
      } else {
        this.receiveForm = { product_id: '', quantity: '', unit_cost: '', reference: '' };
      }
      this.receiveModal = true;
    },

    onReceiveSelect() {
      const p = this.products.find(x => x.id == this.receiveForm.product_id);
      if (p) this.receiveForm.unit_cost = p.unit_cost;
    },

    async receiveStock() {
      this.saving = true;
      try {
        await apiFetch('/inventory/products/receive/', { 
          method: 'POST', 
          body: JSON.stringify(this.receiveForm) 
        });
        this.receiveModal = false;
        this.load(); // Refresh table to show new stock
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Rebuilt products.html with image uploads and receive stock modals")

# ============================================================
# 6. Run Migrations
# ============================================================
print("Running migrations...")
python = get_python()
subprocess.run([str(python), "manage.py", "makemigrations", "inventory"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart server and refresh.")