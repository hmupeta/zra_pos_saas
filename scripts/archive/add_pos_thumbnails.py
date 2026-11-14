import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Ensure Backend returns image_url for the POS
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Ensure the GET request includes image_url safely
if '"image_url": p.image.url if getattr(p, "image", None) else None,' not in v_content:
    v_content = v_content.replace(
        '"category_name": p.category.name,',
        '"category_name": p.category.name,\n                "image_url": p.image.url if getattr(p, "image", None) else None,'
    )
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Backend updated to return image_url in product list.")

# ============================================================
# 2. Update POS Frontend Product Card
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
p_content = pos_path.read_text(encoding="utf-8")

# Replace the product grid button with one that includes an image thumbnail
old_card = '''            <button @click="scanAdd(p.barcode)"
                    :class="lastScan === p.barcode ? 'flash-green' : ''"
                    class="card p-3 text-left hover:shadow-md hover:border-brand-500 transition">
              <div class="font-medium text-sm line-clamp-2 h-10" x-text="p.name"></div>
              <div class="text-xs text-gray-500 mt-1" x-text="p.barcode"></div>
              <div class="flex justify-between items-end mt-2">
                <div class="text-lg font-bold text-brand-700" x-text="formatCurrency(p.selling_price)"></div>
                <div class="text-xs text-gray-400">Stock <span x-text="p.current_stock"></span></div>
              </div>
            </button>'''

new_card = '''            <button @click="scanAdd(p.barcode)"
                    :class="lastScan === p.barcode ? 'flash-green' : ''"
                    class="card p-0 overflow-hidden text-left hover:shadow-lg hover:border-brand-500 transition group flex flex-col">
              
              <!-- Image Thumbnail -->
              <div class="w-full h-32 bg-gray-100 flex items-center justify-center overflow-hidden border-b">
                <template x-if="p.image_url">
                  <img :src="p.image_url" class="w-full h-full object-cover group-hover:scale-105 transition-transform duration-300">
                </template>
                <template x-if="!p.image_url">
                  <div class="text-gray-300 flex flex-col items-center">
                    <i data-lucide="image" class="w-8 h-8 mb-1 opacity-50"></i>
                    <span class="text-[10px] uppercase font-bold tracking-wider opacity-50">No Image</span>
                  </div>
                </template>
              </div>
              
              <!-- Details -->
              <div class="p-3 flex-1 flex flex-col justify-between">
                <div>
                  <div class="font-medium text-sm line-clamp-2 h-10 text-slate-800" x-text="p.name"></div>
                  <div class="text-xs text-gray-400 mt-1 truncate" x-text="p.barcode"></div>
                </div>
                <div class="flex justify-between items-end mt-2">
                  <div class="text-lg font-bold text-brand-700" x-text="formatCurrency(p.selling_price)"></div>
                  <div class="text-xs font-medium px-1.5 py-0.5 rounded" 
                       :class="p.current_stock <= 10 ? 'bg-red-100 text-red-700' : 'bg-gray-100 text-gray-600'">
                    Stock <span x-text="p.current_stock"></span>
                  </div>
                </div>
              </div>
            </button>'''

if old_card in p_content:
    p_content = p_content.replace(old_card, new_card)
    pos_path.write_text(p_content, encoding="utf-8")
    print("✅ Updated POS Product Card with image thumbnail.")
else:
    print("⚠️ Could not find the exact product card block in pos.html. Manual check needed.")

# ============================================================
# 3. Verify Media Files are served in URLs
# ============================================================
urls_path = BACKEND_PATH / "pos_backend" / "urls.py"
urls_content = urls_path.read_text(encoding="utf-8")

if "static(settings.MEDIA_URL" not in urls_content:
    urls_content += """

# --- Serve media files in development ---
from django.conf import settings
from django.conf.urls.static import static
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
"""
    urls_path.write_text(urls_content, encoding="utf-8")
    print("✅ Added media serving to urls.py.")
else:
    print("✅ Media serving already configured in urls.py.")

print("\n🎉 Done! Restart the server and do a HARD REFRESH (Ctrl + Shift + R).")