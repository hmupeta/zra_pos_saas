import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "quotations.html"

content = html_path.read_text(encoding="utf-8")

# ============================================================
# 1. Fix the editQuote function to ensure proper string mapping and rendering
# ============================================================
new_edit_js = '''    async editQuote(id) {
      try {
        const q = await apiFetch(`/sales/quotations/${id}/`);
        
        // Ensure products are loaded
        if (!this.products || this.products.length === 0) {
          this.products = await apiFetch('/inventory/products/');
        }

        // Clear the form first to force Alpine to reset the DOM
        this.form = { id: null, customer_id: '', customer_name: '', valid_until: '', items: [] };
        this.showModal = true; // Open modal while empty

        // Wait for the modal DOM to exist, then populate the data
        this.$nextTick(() => {
          const mappedItems = q.items.map(i => ({
            product_id: String(i.product_id), 
            quantity: i.quantity,
            display_price: i.unit_price // Store for immediate display
          }));

          this.form = {
            id: q.id, 
            customer_id: q.customer_id ? String(q.customer_id) : '', 
            customer_name: q.customer, 
            valid_until: q.valid_until,
            items: mappedItems
          };
        });

      } catch(e) { 
        alert('Error loading quotation: ' + e.message); 
      }
    },'''

pattern = r"async editQuote\(id\) \{.*?\}\s*\},"
if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_edit_js.strip(), content, flags=re.DOTALL)
    print("✅ Rebuilt editQuote with $nextTick to fix rendering.")

# ============================================================
# 2. Fix the <select> dropdown rendering
# ============================================================
old_select = '''                    <td class="pr-2">
                      <select x-model="line.product_id" class="input-field text-sm py-1" required>
                        <option value="" disabled>-- Select Product --</option>
                        <template x-for="p in products" :key="p.id">
                          <option :value="String(p.id)" x-text="p.name + ' (' + formatCurrency(p.selling_price) + ')'"></option>
                        </template>
                      </select>
                    </td>'''

new_select = '''                    <td class="pr-2">
                      <select x-model="line.product_id" class="input-field text-sm py-1" required>
                        <option value="" disabled>-- Select Product --</option>
                        <template x-for="p in products" :key="p.id">
                          <!-- Using :value="p.id" and ensuring x-model matches -->
                          <option :value="p.id" x-text="p.name + ' (' + formatCurrency(p.selling_price) + ')'"></option>
                        </template>
                      </select>
                    </td>'''

if old_select in content:
    content = content.replace(old_select, new_select)
    print("✅ Simplified the <select> option values.")
else:
    # Fallback regex if exact string doesn't match
    pattern_sel = r'<select x-model="line\.product_id".*?</select>'
    content = re.sub(pattern_sel, new_select.strip(), content, flags=re.DOTALL)
    print("✅ Fixed <select> using regex.")

# ============================================================
# 3. Fix the getPrice function to handle the initial render
# ============================================================
old_get_price = '''    getPrice(id) {
      const p = this.products.find(x => x.id == id);
      return p ? formatCurrency(p.selling_price) : '-';
    },'''

new_get_price = '''    getPrice(id) {
      if (!id) return '-';
      // Use String() on both sides for a safe comparison
      const p = this.products.find(x => String(x.id) === String(id));
      return p ? formatCurrency(p.selling_price) : '-';
    },'''

if old_get_price in content:
    content = content.replace(old_get_price, new_get_price)
    print("✅ Hardened getPrice function.")

# ============================================================
# 4. Ensure the table rows have a unique key to force DOM updates
# ============================================================
old_tr = '''<template x-for="(line, idx) in form.items" :key="idx">'''
new_tr = '''<template x-for="(line, idx) in form.items" :key="'item-' + idx + '-' + line.product_id">'''

if old_tr in content:
    content = content.replace(old_tr, new_tr)
    print("✅ Updated x-for key to force re-render.")

html_path.write_text(content, encoding="utf-8")
print("\n🎉 Done! Restart the server and hard refresh the Quotations page.")