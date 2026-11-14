import os
import re
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Ensure Django serves Media files (Images) in Development
# ============================================================
urls_path = BACKEND_PATH / "pos_backend" / "urls.py"
urls_content = urls_path.read_text(encoding="utf-8")

if "static(settings.MEDIA_URL" not in urls_content:
    # Add media serving if missing
    urls_content += """

# --- Serve media files in development ---
from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""
    urls_path.write_text(urls_content, encoding="utf-8")
    print("✅ Added media file serving to urls.py (images will now display)")
else:
    print("✅ Media file serving already configured")

# ============================================================
# 2. Rebuild the View Modal in products.html (Bulletproof)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"
h_content = html_path.read_text(encoding="utf-8")

# Replace the entire View Modal with a simpler, more robust version
view_modal_pattern = r"<!-- View Product Modal -->.*?</template>"

new_view_modal = '''<!-- View Product Modal -->
    <template x-if="viewModal">
      <div class="fixed inset-0 bg-black/70 flex items-center justify-center z-[9999] p-4">
        <div class="bg-white rounded-xl max-w-lg w-full overflow-hidden shadow-2xl">
          
          <!-- Close Button -->
          <div class="flex justify-between items-center p-4 border-b bg-gray-50">
            <h2 class="text-xl font-bold text-slate-900" x-text="viewModal.name"></h2>
            <button @click="viewModal = null" class="text-gray-500 hover:text-red-500 text-2xl font-bold px-2">&times;</button>
          </div>

          <!-- Image -->
          <div class="h-64 bg-gray-100 flex items-center justify-center relative">
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

          <!-- Details -->
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

            <!-- Image Link (proof it exists) -->
            <template x-if="viewModal.image_url">
              <a :href="viewModal.image_url" target="_blank" class="block text-center text-xs text-blue-600 hover:underline mt-2">
                🔗 Click here to open image in new tab (proof it was saved)
              </a>
            </template>

            <div class="flex gap-2 pt-4 border-t">
              <button @click="viewModal = null" class="btn-secondary flex-1">Close</button>
              <button @click="viewModal = null; openProductModal(viewModal.id)" class="btn-primary flex-1">Edit This Product</button>
            </div>
          </div>
        </div>
      </div>
    </template>'''

if re.search(view_modal_pattern, h_content, flags=re.DOTALL):
    h_content = re.sub(view_modal_pattern, new_view_modal, h_content, flags=re.DOTALL)
    print("✅ Replaced View Modal with a bulletproof version")
else:
    print("⚠️ Could not find the View Modal block")

# ============================================================
# 3. Update viewProduct function with debugging alerts
# ============================================================
old_func = '''    viewProduct(product) {
      this.viewModal = product;
      setTimeout(() => { lucide.createIcons(); }, 50);
    },'''

new_func = '''    viewProduct(product) {
      console.log("=== VIEW PRODUCT CLICKED ===");
      console.log("Product data:", product);
      console.log("Image URL:", product.image_url);
      console.log("Attempting to set viewModal...");
      
      this.viewModal = product;
      this.$nextTick(() => {
        console.log("viewModal state now:", this.viewModal);
        console.log("Modal should be visible:", this.viewModal !== null);
      });
    },'''

if old_func in h_content:
    h_content = h_content.replace(old_func, new_func)
    print("✅ Added console logging to viewProduct function")
else:
    print("⚠️ Could not find viewProduct function")

html_path.write_text(h_content, encoding="utf-8")

print("\n" + "="*60)
print("  🎉 FIXES APPLIED!")
print("="*60)
print("""
NEXT STEPS:
1. Restart your server:
   python manage.py runserver

2. Open POS in browser and press Ctrl + Shift + R to hard refresh

3. Open the BROWSER CONSOLE (F12 key, then click Console tab)

4. Go to Products and click VIEW on any product
   - You should see console logs like "=== VIEW PRODUCT CLICKED ==="
   - The modal will pop up showing the details and image
   - If there's an image, you'll see a clickable link to open it directly

5. To check if an image uploaded worked:
   - Look at the product row - if there's a thumbnail, it worked
   - Or open a product's View modal - if the image URL is present, it worked
""")