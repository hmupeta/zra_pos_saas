import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# Find the existing product card block
# We use a regex to match the entire <button> element for the product card
pattern = r"<button @click=\"scanAdd\(p\.barcode\)\"[\s\S]*?</button>"

new_card = '''<button @click="scanAdd(p.barcode)"
                    :class="lastScan === p.barcode ? 'ring-4 ring-green-400 bg-green-50' : ''"
                    class="bg-white rounded-2xl border border-gray-100 shadow-sm hover:shadow-xl hover:-translate-y-1 transition-all duration-300 text-left flex flex-col overflow-hidden group">
              
              <!-- Image Container -->
              <div class="relative w-full h-40 bg-gradient-to-b from-gray-50 to-gray-100 flex items-center justify-center overflow-hidden p-4">
                <template x-if="p.image_url">
                  <img :src="p.image_url" class="w-full h-full object-contain group-hover:scale-110 transition-transform duration-500 ease-out drop-shadow-md">
                </template>
                <template x-if="!p.image_url">
                  <div class="flex flex-col items-center justify-center text-slate-300">
                    <i data-lucide="package-open" class="w-12 h-12 mb-1 opacity-40"></i>
                    <span class="text-[10px] font-bold tracking-widest uppercase opacity-60">No Image</span>
                  </div>
                </template>
                
                <!-- Out of Stock Overlay -->
                <template x-if="p.current_stock <= 0">
                  <div class="absolute inset-0 bg-white/70 backdrop-blur-[2px] flex items-center justify-center">
                    <span class="bg-red-500 text-white text-xs font-bold px-3 py-1 rounded-full shadow-lg">OUT OF STOCK</span>
                  </div>
                </template>
              </div>
              
              <!-- Details Container -->
              <div class="p-4 flex-1 flex flex-col justify-between">
                <div>
                  <div class="font-bold text-slate-800 text-sm leading-tight line-clamp-2 min-h-[2.5rem]" x-text="p.name"></div>
                  <div class="text-[11px] text-slate-400 font-mono mt-1 truncate" x-text="p.barcode"></div>
                </div>
                
                <div class="flex justify-between items-end mt-4">
                  <div class="flex flex-col">
                    <span class="text-[10px] text-slate-400 uppercase font-bold tracking-wider mb-0.5">Price</span>
                    <div class="text-lg font-extrabold text-brand-700" x-text="formatCurrency(p.selling_price)"></div>
                  </div>
                  
                  <div class="text-[11px] font-bold px-2.5 py-1 rounded-full border" 
                       :class="p.current_stock <= 10 ? 'bg-red-50 text-red-600 border-red-100' : 'bg-slate-50 text-slate-600 border-slate-200'">
                    <span x-text="p.current_stock"></span> <span class="font-medium opacity-70">left</span>
                  </div>
                </div>
              </div>
            </button>'''

if re.search(pattern, content):
    content = re.sub(pattern, new_card, content, count=1)
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Beautifully redesigned the POS product cards.")
else:
    print("⚠️ Could not find the product card block. Please check pos.html manually.")

# Ensure Lucide icons are refreshed after products load
load_pattern = r"this.products = await apiFetch\('/inventory/products/'\);"
if load_pattern in content:
    content = content.replace(
        load_pattern,
        "this.products = await apiFetch('/inventory/products/');\n        setTimeout(() => { lucide.createIcons(); }, 100);"
    )
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Added Lucide icon refresh on product load.")

print("\n🎉 Done! Restart the server and do a HARD REFRESH (Ctrl + Shift + R).")