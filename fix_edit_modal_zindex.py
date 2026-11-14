import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"

full_html = '''
{% extends "pos/base.html" %}
{% block title %}Products{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="productsPage()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Products & Inventory</h1>
      <div class="flex gap-2">
        <button @click="showImportModal = true" class="btn-secondary bg-green-50 text-green-700 border-green-200 hover:bg-green-100">
          <i data-lucide="upload" class="w-4 h-4 inline mr-1"></i> Import CSV
        </button>
        <button @click="exportCsv()" class="btn-secondary">Export CSV</button>
        <button @click="openReceiveModal(null)" class="btn-secondary">+ Receive Stock</button>
        <button @click="openProductModal(null)" class="btn-primary">+ New Product</button>
      </div>
    </div>

    <div class="mb-4">
      <input type="text" x-model="search" @input.debounce.300ms="load()" placeholder="Search by name or barcode..." class="input-field max-w-md">
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Product</th>
            <th class="px-4 py-3">Barcode</th>
            <th class="px-4 py-3 text-right">Cost</th>
            <th class="px-4 py-3 text-right">Selling</th>
            <th class="px-4 py-3 text-center">Discount</th>
            <th class="px-4 py-3 text-center">Stock</th>
            <th class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="p in products" :key="p.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3">
                <div class="flex items-center gap-3">
                  <div class="w-10 h-10 bg-gray-100 rounded overflow-hidden flex-shrink-0 border">
                    <template x-if="p.image_url">
                      <img :src="p.image_url" class="w-full h-full object-cover">
                    </template>
                    <template x-if="!p.image_url">
                      <div class="w-full h-full flex items-center justify-center text-xs text-gray-400">No Img</div>
                    </template>
                  </div>
                  <div>
                    <div class="font-medium text-slate-800" x-text="p.name"></div>
                    <div class="text-xs text-gray-500" x-text="p.category_name"></div>
                  </div>
                </div>
              </td>
              <td class="px-4 py-3 font-mono text-xs" x-text="p.barcode"></td>
              <td class="px-4 py-3 text-right text-gray-500" x-text="formatCurrency(p.unit_cost)"></td>
              <td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(p.selling_price)"></td>
              <td class="px-4 py-3 text-center">
                <span x-show="p.discount_percentage > 0" class="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-bold" x-text="p.discount_percentage + '%'"></span>
                <span x-show="p.discount_percentage === 0" class="text-gray-400 text-xs">-</span>
              </td>
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded text-xs" :class="p.current_stock <= 10 ? 'bg-red-100 text-red-700' : 'bg-green-100 text-green-700'" x-text="p.current_stock"></span>
              </td>
              <td class="px-4 py-3 text-right space-x-3">
                <button @click="viewProduct(p)" class="text-xs text-blue-600 hover:underline font-medium">View</button>
                <button @click="openProductModal(p.id)" class="text-xs text-gray-500 hover:text-brand-600 hover:underline font-medium">Edit</button>
                <button @click="openReceiveModal(p)" class="text-xs text-brand-600 hover:underline font-medium">Add Stock</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="products.length === 0" class="p-8 text-center text-gray-400">No products found</div>
    </div>

    <!-- View Product Modal (High Z-Index) -->
    <template x-if="viewModal">
      <div class="fixed inset-0 bg-black/70 flex items-center justify-center z-[9000] p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl max-w-lg w-full overflow-hidden shadow-2xl">
          <div class="flex justify-between items-center p-4 border-b bg-gray-50">
            <h2 class="text-xl font-bold text-slate-900" x-text="viewModal.name"></h2>
            <button @click="viewModal = null" class="text-gray-500 hover:text-red-500 text-2xl font-bold px-2">&times;</button>
          </div>
          <div class="h-64 bg-gray-100 flex items-center justify-center">
            <template x-if="viewModal.image_url">
              <img :src="viewModal.image_url" class="max-h-full max-w-full object-contain">
            </template>
            <template x-if="!viewModal.image_url">
              <div class="text-center text-gray-400">
                <div class="text-4xl mb-2">📷</div>
                <div class="text-sm font-medium">No image uploaded yet</div>
              </div>
            </template>
          </div>
          <div class="p-6 space-y-3">
            <div class="grid grid-cols-2 gap-4">
              <div>
                <div class="text-xs text-gray-500 uppercase font-bold">Barcode</div>
                <div class="font-mono text-sm" x-text="viewModal.barcode"></div>
              </div>
              <div>
                <div class="text-xs text-gray-500 uppercase font-bold">Category</div>
                <div class="text-sm font-medium" x-text="viewModal.category_name"></div>
              </div>
              <div>
                <div class="text-xs text-gray-500 uppercase font-bold">Cost Price</div>
                <div class="text-sm" x-text="formatCurrency(viewModal.unit_cost)"></div>
              </div>
              <div>
                <div class="text-xs text-gray-500 uppercase font-bold">Selling Price</div>
                <div class="text-lg font-bold text-brand-700" x-text="formatCurrency(viewModal.selling_price)"></div>
              </div>
              <div>
                <div class="text-xs text-gray-500 uppercase font-bold">In Stock</div>
                <div class="text-lg font-bold" :class="viewModal.current_stock <= 10 ? 'text-red-600' : 'text-green-600'" x-text="viewModal.current_stock"></div>
              </div>
              <div>
                <div class="text-xs text-gray-500 uppercase font-bold">Discount</div>
                <div class="text-sm font-bold text-red-600" x-text="viewModal.discount_percentage > 0 ? viewModal.discount_percentage + '%' : 'None'"></div>
              </div>
            </div>
            <div class="flex gap-2 pt-4 border-t">
              <button @click="viewModal = null" class="btn-secondary flex-1">Close</button>
              <button @click="editFromView()" class="btn-primary flex-1">Edit This Product</button>
            </div>
          </div>
        </div>
      </div>
    </template>

    <!-- New/Edit Product Modal (Extreme Z-Index to be above View Modal) -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/70 flex items-center justify-center z-[9999] p-4">
        <div class="bg-white rounded-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
          <h2 class="text-xl font-bold mb-4" x-text="form.id ? 'Edit Product' : 'New Product'"></h2>
          <form @submit.prevent="saveProduct()" class="space-y-3">
            <div class="grid grid-cols-2 gap-3">
              <input placeholder="Barcode" x-model="form.barcode" class="input-field">
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
                <label class="block text-xs text-gray-500 mb-1">Discount % (Manager Only)</label>
                <input type="number" step="0.01" x-model="form.discount_percentage" class="input-field" placeholder="0.00">
              </div>
              <div>
                <label class="block text-xs text-gray-500 mb-1">Reorder Level</label>
                <input type="number" step="0.01" x-model="form.reorder_level" class="input-field">
              </div>
            </div>

            <div x-show="!form.id">
              <label class="block text-xs text-gray-500 mb-1">Opening Stock</label>
              <input type="number" step="0.01" x-model="form.current_stock" class="input-field">
            </div>

            <div>
              <label class="block text-xs text-gray-500 mb-1">Product Image</label>
              <div class="flex items-center gap-4">
                <div class="w-16 h-16 bg-gray-100 rounded-lg overflow-hidden border flex-shrink-0">
                  <template x-if="imagePreview">
                    <img :src="imagePreview" class="w-full h-full object-cover">
                  </template>
                  <template x-if="!imagePreview">
                    <div class="w-full h-full flex items-center justify-center text-xs text-gray-400">No Img</div>
                  </template>
                </div>
                <input type="file" @change="handleFile" accept="image/*" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700">
              </div>
            </div>

            <div class="flex gap-2 mt-6">
              <button type="button" @click="showModal = false; resetForm()" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1" :disabled="saving">
                <span x-show="!saving">Save Product</span>
                <span x-show="saving">Saving...</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </template>

    <!-- Receive Stock Modal -->
    <template x-if="receiveModal">
      <div class="fixed inset-0 bg-black/70 flex items-center justify-center z-[9999] p-4">
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
              <input type="text" x-model="receiveForm.reference" class="input-field">
            </div>
            <div class="flex gap-2 mt-4">
              <button type="button" @click="receiveModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1" :disabled="saving">Add to Stock</button>
            </div>
          </form>
        </div>
      </div>
    </template>

    <!-- Import CSV Modal -->
    <template x-if="showImportModal">
      <div class="fixed inset-0 bg-black/70 flex items-center justify-center z-[9999] p-4" @click.self="showImportModal = false">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">Bulk Import Products</h2>
            <button @click="showImportModal = false" class="text-gray-500 hover:text-red-500 font-bold text-xl px-2">&times;</button>
          </div>
          
          <div class="bg-blue-50 text-blue-800 text-sm p-4 rounded-lg mb-4">
            <p class="mb-2"><strong>Instructions:</strong></p>
            <ol class="list-decimal ml-4 space-y-1">
              <li>Download the template below.</li>
              <li>Fill in your products (do not change the column headers).</li>
              <li>Upload the saved CSV file.</li>
            </ol>
            <a href="/api/inventory/products/template/" class="inline-block mt-3 text-blue-600 font-bold hover:underline">
              ⬇️ Download CSV Template
            </a>
          </div>

          <form @submit.prevent="uploadCsv()" class="space-y-4">
            <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:bg-gray-50 transition relative">
              <input type="file" accept=".csv" @change="handleCsvUpload" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer">
              <i data-lucide="file-spreadsheet" class="w-8 h-8 text-gray-400 mx-auto mb-2"></i>
              <p class="text-sm font-medium text-gray-700" x-text="csvFile ? csvFile.name : 'Click or drag CSV file here'"></p>
              <p class="text-xs text-gray-500 mt-1" x-show="!csvFile">Only .csv files are allowed</p>
            </div>

            <div class="flex gap-2 pt-2">
              <button type="button" @click="showImportModal = false; csvFile = null; importResult = null;" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1" :disabled="!csvFile || uploading">
                <span x-show="!uploading">Upload & Import</span>
                <span x-show="uploading">Processing...</span>
              </button>
            </div>
          </form>
          
          <div x-show="importResult" class="mt-4 p-4 rounded-lg" :class="importResult?.errors?.length > 0 ? 'bg-yellow-50' : 'bg-green-50'">
            <p class="font-bold text-sm mb-2" x-text="'Import Complete: ' + importResult?.created + ' new products added.'"></p>
            <template x-if="importResult?.errors?.length > 0">
              <div>
                <p class="text-xs text-red-600 font-bold mb-1">Some rows were skipped:</p>
                <ul class="text-xs text-red-600 list-disc ml-4 max-h-24 overflow-y-auto">
                  <template x-for="err in importResult.errors">
                    <li x-text="err"></li>
                  </template>
                </ul>
              </div>
            </template>
          </div>
        </div>
      </div>
    </template>

  </div>
</div>

<script>
function productsPage() {
  return {
    products: [], categories: [], taxes: [], search: '',
    showModal: false, receiveModal: false, showImportModal: false, viewModal: null, saving: false,
    csvFile: null, uploading: false, importResult: null,
    imagePreview: null,
    
    form: { id: null, barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', discount_percentage: 0, current_stock: 0, reorder_level: 10 },
    imageFile: null,
    receiveForm: { product_id: '', quantity: '', unit_cost: '', reference: '' },

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.products = await apiFetch(`/inventory/products/?search=${this.search}`);
        this.categories = await apiFetch('/inventory/categories/');
        this.taxes = await apiFetch('/inventory/tax-rates/');
      } catch(e) { alert(e.message); }
    },

    handleFile(e) {
      if (e.target.files.length > 0) {
        this.imageFile = e.target.files[0];
        this.imagePreview = URL.createObjectURL(this.imageFile);
      }
    },

    resetForm() {
      this.form = { id: null, barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', discount_percentage: 0, current_stock: 0, reorder_level: 10 };
      this.imageFile = null;
      this.imagePreview = null;
    },

    viewProduct(product) {
      this.viewModal = product;
    },

    editFromView() {
      const id = this.viewModal.id;
      this.viewModal = null;
      this.openProductModal(id);
    },

    async openProductModal(id) {
      if (!id) {
        this.resetForm();
        this.showModal = true;
        return;
      }
      try {
        console.log("Fetching product for edit:", id);
        const p = await apiFetch(`/inventory/products/?id=${id}`);
        console.log("Product data loaded:", p);
        
        this.form = { 
          id: p.id, barcode: p.barcode, name: p.name, 
          category_id: p.category_id, tax_rate_id: p.tax_rate_id, 
          unit_cost: p.unit_cost, selling_price: p.selling_price, 
          discount_percentage: p.discount_percentage, 
          current_stock: p.current_stock, reorder_level: p.reorder_level 
        };
        this.imageFile = null;
        this.imagePreview = p.image_url; 
        this.showModal = true;
      } catch(e) { alert('Failed to load product: ' + e.message); }
    },

    async saveProduct() {
      this.saving = true;
      try {
        const fd = new FormData();
        Object.keys(this.form).forEach(k => fd.append(k, this.form[k]));
        if (this.imageFile) fd.append('image', this.imageFile);

        const method = this.form.id ? 'PUT' : 'POST';
        const res = await apiFetch('/inventory/products/', { method: method, body: fd });
        
        console.log("Save response:", res);
        alert('✅ Product saved successfully!');
        this.showModal = false;
        this.resetForm();
        this.load();
      } catch(e) { 
        console.error("Save error:", e);
        alert(e.response?.data?.error || e.message); 
      }
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
        await apiFetch('/inventory/products/receive/', { method: 'POST', body: JSON.stringify(this.receiveForm) });
        this.receiveModal = false;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    },

    async exportCsv() {
      try {
        const res = await fetch('/api/auth/export/products/', {
          headers: { 'Authorization': `Token ${localStorage.getItem('token')}` }
        });
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'products.csv'; a.click();
      } catch (e) { alert(e.message); }
    },

    handleCsvUpload(e) {
      if (e.target.files.length > 0) {
        this.csvFile = e.target.files[0];
        this.importResult = null;
      }
    },

    async uploadCsv() {
      if (!this.csvFile) return;
      this.uploading = true;
      this.importResult = null;
      try {
        const fd = new FormData();
        fd.append('file', this.csvFile);
        const res = await apiFetch('/inventory/products/import/', { method: 'POST', body: fd });
        this.importResult = res;
        this.csvFile = null;
        this.load();
      } catch(e) {
        alert(e.response?.data?.error || e.message);
      } finally {
        this.uploading = false;
      }
    }
  }
}
</script>
{% endblock %}
'''

html_path.write_text(full_html.strip(), encoding="utf-8")
print("✅ Completely rebuilt products.html.")
print("✅ Fixed Z-Index conflicts (Edit modal is now z-[9999], View is z-[9000]).")
print("✅ Added console logs to help debug.")
print("\n🎉 Done! Restart the server and do a HARD REFRESH (Ctrl + Shift + R).")