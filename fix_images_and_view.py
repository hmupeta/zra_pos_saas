import os
import re
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Fix Backend Parsers for Image Uploads
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Add parser classes import
if "MultiPartParser" not in v_content:
    v_content = "from rest_framework.parsers import MultiPartParser, FormParser\n" + v_content

# Add decorator to products_list
if "@parser_classes([MultiPartParser, FormParser])" not in v_content:
    v_content = v_content.replace(
        "@api_view(['GET', 'POST', 'PUT'])",
        "@api_view(['GET', 'POST', 'PUT'])\n@parser_classes([MultiPartParser, FormParser])"
    )
views_path.write_text(v_content, encoding="utf-8")
print("✅ Fixed backend parsers to accept image uploads correctly.")

# ============================================================
# 2. Update Frontend Products UI (Add View Modal & Image Previews)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"
h_content = html_path.read_text(encoding="utf-8")

# A. Add "View" button to the table
old_actions = '''              <td class="px-4 py-3 text-right space-x-3">
                <button @click="openProductModal(p.id)" class="text-xs text-gray-500 hover:text-brand-600 hover:underline">Edit</button>
                <button @click="openReceiveModal(p)" class="text-xs text-brand-600 hover:underline">Add Stock</button>
              </td>'''
new_actions = '''              <td class="px-4 py-3 text-right space-x-3">
                <button @click="viewProduct(p)" class="text-xs text-blue-600 hover:underline font-medium">View</button>
                <button @click="openProductModal(p.id)" class="text-xs text-gray-500 hover:text-brand-600 hover:underline font-medium">Edit</button>
                <button @click="openReceiveModal(p)" class="text-xs text-brand-600 hover:underline font-medium">Add Stock</button>
              </td>'''
h_content = h_content.replace(old_actions, new_actions)

# B. Add Image Preview to Edit/New Modal
old_form_img = '''            <div>
              <label class="block text-xs text-gray-500 mb-1">Product Image</label>
              <input type="file" @change="handleFile" accept="image/*" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700">
            </div>'''
new_form_img = '''            <div>
              <label class="block text-xs text-gray-500 mb-1">Product Image</label>
              <div class="flex items-center gap-4">
                <div class="w-16 h-16 bg-gray-100 rounded-lg overflow-hidden border flex-shrink-0">
                  <template x-if="imagePreview">
                    <img :src="imagePreview" class="w-full h-full object-cover">
                  </template>
                  <template x-if="!imagePreview && form.image_url">
                    <img :src="form.image_url" class="w-full h-full object-cover">
                  </template>
                  <template x-if="!imagePreview && !form.image_url">
                    <div class="w-full h-full flex items-center justify-center text-xs text-gray-400">No Img</div>
                  </template>
                </div>
                <input type="file" @change="handleFile" accept="image/*" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700">
              </div>
            </div>'''
h_content = h_content.replace(old_form_img, new_form_img)

# C. Add the View Product Modal
view_modal = '''
    <!-- View Product Modal -->
    <template x-if="viewModal">
      <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-50 p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl max-w-md w-full overflow-hidden shadow-2xl">
          <div class="relative h-64 bg-gray-100">
            <template x-if="viewModal.image_url">
              <img :src="viewModal.image_url" class="w-full h-full object-contain bg-white">
            </template>
            <template x-if="!viewModal.image_url">
              <div class="w-full h-full flex items-center justify-center text-gray-400">
                <i data-lucide="image-off" class="w-12 h-12"></i>
              </div>
            </template>
            <button @click="viewModal = null" class="absolute top-3 right-3 bg-black/50 text-white rounded-full p-1 hover:bg-black/70">
              <i data-lucide="x" class="w-5 h-5"></i>
            </button>
          </div>
          
          <div class="p-6">
            <div class="flex justify-between items-start mb-4">
              <div>
                <h2 class="text-2xl font-bold text-slate-900" x-text="viewModal.name"></h2>
                <p class="text-sm text-brand-600 font-medium" x-text="viewModal.category_name"></p>
              </div>
              <div class="text-right">
                <div class="text-xs text-gray-500 uppercase tracking-wider">Stock</div>
                <div class="text-xl font-bold" :class="viewModal.current_stock <= 10 ? 'text-red-600' : 'text-green-600'" x-text="viewModal.current_stock"></div>
              </div>
            </div>

            <div class="grid grid-cols-2 gap-4 border-t border-gray-100 pt-4">
              <div>
                <div class="text-xs text-gray-500 uppercase tracking-wider">Barcode</div>
                <div class="font-mono text-sm text-slate-800" x-text="viewModal.barcode"></div>
              </div>
              <div>
                <div class="text-xs text-gray-500 uppercase tracking-wider">Unit Cost</div>
                <div class="font-medium text-slate-800" x-text="formatCurrency(viewModal.unit_cost)"></div>
              </div>
              <div>
                <div class="text-xs text-gray-500 uppercase tracking-wider">Selling Price</div>
                <div class="font-bold text-lg text-brand-700" x-text="formatCurrency(viewModal.selling_price)"></div>
              </div>
              <div>
                <div class="text-xs text-gray-500 uppercase tracking-wider">Discount</div>
                <div class="font-bold text-red-600" x-text="viewModal.discount_percentage > 0 ? viewModal.discount_percentage + '%' : 'None'"></div>
              </div>
              <div>
                <div class="text-xs text-gray-500 uppercase tracking-wider">Tax Rate</div>
                <div class="font-medium text-slate-800" x-text="viewModal.tax_rate + '%'"></div>
              </div>
            </div>

            <div class="mt-6 flex justify-end">
              <button @click="viewModal = null" class="btn-primary">Close</button>
            </div>
          </div>
        </div>
      </div>
    </template>
'''
h_content = h_content.replace("  </div>\n</div>\n<script>", view_modal + "\n  </div>\n</div>\n<script>")

# D. Update JavaScript State
h_content = h_content.replace(
    "showModal: false, receiveModal: false, showImportModal: false, saving: false,",
    "showModal: false, receiveModal: false, showImportModal: false, viewModal: null, saving: false,\n    imagePreview: null,"
)

# E. Update handleFile to set preview
old_handle_file = '''    handleFile(e) {
      if (e.target.files.length > 0) this.imageFile = e.target.files[0];
    },'''
new_handle_file = '''    handleFile(e) {
      if (e.target.files.length > 0) {
        this.imageFile = e.target.files[0];
        this.imagePreview = URL.createObjectURL(this.imageFile);
      }
    },'''
h_content = h_content.replace(old_handle_file, new_handle_file)

# F. Update resetForm and openProductModal to clear previews
h_content = h_content.replace(
    "this.imageFile = null;\n    },\n\n    async openProductModal(id) {",
    "this.imageFile = null;\n      this.imagePreview = null;\n    },\n\n    async openProductModal(id) {"
)
h_content = h_content.replace(
    "this.imageFile = null;\n        this.showModal = true;\n      } catch(e) { alert(e.message); }",
    "this.imageFile = null;\n        this.imagePreview = p.image_url; // Set existing image as preview\n        this.showModal = true;\n      } catch(e) { alert(e.message); }"
)

# G. Add viewProduct function
h_content = h_content.replace(
    "    async openProductModal(id) {",
    "    viewProduct(product) {\n      this.viewModal = product;\n    },\n\n    async openProductModal(id) {"
)

html_path.write_text(h_content, encoding="utf-8")
print("✅ Added View Modal, Image Previews, and fixed JS state.")

print("\n🎉 Done! Restart the server and hard refresh (Ctrl + Shift + R).")