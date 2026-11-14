import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# 1. Fix the init() function to gracefully handle errors and force products to load
old_init = """    async init() {
      if (!requireAuth() || !requireBranch()) return;

      window.addEventListener('barcode-scanned', (e) => this.scanAdd(e.detail.code));

      try {
        this.shift = await apiFetch('/sales/current-shift/').catch((e) => {
          if (e.response?.status === 404) return null; throw e;
        });
        this.products = await apiFetch('/inventory/products/');
        
        if (this.shift) {
          this.cart = await apiFetch('/sales/cart/');
        } else {
          this.openShiftModal = true;
        }

        // Load payment gateways
        try {
          this.paymentConfigs = await apiFetch('/payments/configs/');
          if (this.paymentConfigs && Array.isArray(this.paymentConfigs)) {
            const momoConfigs = this.paymentConfigs.filter(c => c.provider.includes('DIRECT'));
            this.availableMomoProviders = [...new Set(momoConfigs.map(c => c.provider))];
            if (this.availableMomoProviders.length > 0) {
              this.selectedProvider = this.availableMomoProviders[0];
            }
          }
        } catch (e) { console.error("Could not load gateways", e); }

        const branches = await apiFetch('/auth/branches/');
        const cur = branches.find(b => String(b.id) === String(getBranchId()));
        if (cur) document.getElementById('pos-branch').textContent = cur.name;
      } catch (e) {
        alert('Failed to load POS: ' + e.message);
      }
    },"""

new_init = """    async init() {
      if (!requireAuth() || !requireBranch()) return;

      window.addEventListener('barcode-scanned', (e) => this.scanAdd(e.detail.code));

      // 1. Load Products FIRST (so the grid populates immediately)
      try {
        const prodData = await apiFetch('/inventory/products/');
        this.products = Array.isArray(prodData) ? prodData : [];
      } catch (e) {
        console.error("Failed to load products:", e);
        alert("Error loading products: " + e.message);
      }

      // 2. Load Shift
      try {
        this.shift = await apiFetch('/sales/current-shift/').catch((e) => {
          if (e.response?.status === 404) return null; throw e;
        });
        if (this.shift) {
          this.cart = await apiFetch('/sales/cart/');
        } else {
          this.openShiftModal = true;
        }
      } catch (e) {
        console.error("Failed to load shift:", e);
      }

      // 3. Load Payment Gateways
      try {
        this.paymentConfigs = await apiFetch('/payments/configs/');
        if (this.paymentConfigs && Array.isArray(this.paymentConfigs)) {
          const momoConfigs = this.paymentConfigs.filter(c => c.provider.includes('DIRECT'));
          this.availableMomoProviders = [...new Set(momoConfigs.map(c => c.provider))];
          if (this.availableMomoProviders.length > 0) {
            this.selectedProvider = this.availableMomoProviders[0];
          }
        }
      } catch (e) { 
        console.error("Could not load gateways", e); 
      }

      // 4. Load Branch Name
      try {
        const branches = await apiFetch('/auth/branches/');
        const cur = branches.find(b => String(b.id) === String(getBranchId()));
        if (cur) document.getElementById('pos-branch').textContent = cur.name;
      } catch (e) {
        console.error("Failed to load branches:", e);
      }
    },"""

if old_init in content:
    content = content.replace(old_init, new_init)
    print("✅ Replaced init() function with robust error handling.")
else:
    print("⚠️ Could not find the exact init() block. Attempting regex replace.")
    # Regex fallback if spacing changed
    pattern = r"    async init\(\) \{.*?alert\('Failed to load POS: ' \+ e\.message\);\s*\}\s*\},"
    content = re.sub(pattern, new_init, content, flags=re.DOTALL)
    print("✅ Replaced init() using regex.")

# 2. Fix the filteredProducts getter to handle undefined safely
old_getter = """    get filteredProducts() {
      const q = this.search.toLowerCase();
      return q ? this.products.filter(p => p.name.toLowerCase().includes(q) || p.barcode.includes(q)) : this.products;
    },"""

new_getter = """    get filteredProducts() {
      if (!Array.isArray(this.products)) return [];
      const q = this.search.toLowerCase();
      return q ? this.products.filter(p => p.name && p.name.toLowerCase().includes(q) || p.barcode.includes(q)) : this.products;
    },"""

if old_getter in content:
    content = content.replace(old_getter, new_getter)
    print("✅ Hardened filteredProducts getter against missing array.")
else:
    pattern = r"    get filteredProducts\(\) \{.*?\},"
    content = re.sub(pattern, new_getter, content, flags=re.DOTALL)
    print("✅ Hardened filteredProducts getter using regex.")

pos_path.write_text(content, encoding="utf-8")
print("\n🎉 Done! Restart the server and do a HARD REFRESH (Ctrl + Shift + R).")