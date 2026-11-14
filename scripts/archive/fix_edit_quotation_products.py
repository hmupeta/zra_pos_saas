import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "quotations.html"

content = html_path.read_text(encoding="utf-8")

# ============================================================
# 1. Fix the editQuote function to ensure ID types match
# ============================================================
old_edit_js = '''    async editQuote(id) {
      try {
        const q = await apiFetch(`/sales/quotations/${id}/`);
        this.form = {
          id: q.id, customer_id: q.customer_id || '', 
          customer_name: q.customer, valid_until: q.valid_until,
          items: q.items.map(i => ({ product_id: i.product_id, quantity: i.quantity }))
        };
        this.showModal = true;
      } catch(e) { alert(e.message); }
    },'''

new_edit_js = '''    async editQuote(id) {
      try {
        const q = await apiFetch(`/sales/quotations/${id}/`);
        this.form = {
          id: q.id, 
          customer_id: q.customer_id ? String(q.customer_id) : '', 
          customer_name: q.customer, 
          valid_until: q.valid_until,
          // Ensure product_id is a string to match the <option> value
          items: q.items.map(i => ({ product_id: String(i.product_id), quantity: i.quantity }))
        };
        this.showModal = true;
      } catch(e) { alert(e.message); }
    },'''

if old_edit_js in content:
    content = content.replace(old_edit_js, new_edit_js)
    print("✅ Fixed editQuote to ensure product IDs match the dropdown values.")
else:
    print("⚠️ Could not find the exact editQuote function. Checking for variations...")

# ============================================================
# 2. Add a "Remove Line" button to the items loop in the modal
# ============================================================
# Find the table row inside the modal
old_tr = '''                <template x-for="(line, idx) in form.items" :key="idx">
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
                </template>'''

new_tr = '''                <template x-for="(line, idx) in form.items" :key="idx">
                  <tr>
                    <td class="pr-2">
                      <select x-model="line.product_id" class="input-field text-sm py-1" required>
                        <option value="">Select Product...</option>
                        <template x-for="p in products" :key="p.id">
                          <option :value="String(p.id)" x-text="p.name + ' (' + formatCurrency(p.selling_price) + ')'"></option>
                        </template>
                      </select>
                    </td>
                    <td class="pr-2"><input type="number" min="1" x-model="line.quantity" class="input-field text-sm py-1 text-right" required></td>
                    <td class="text-right text-gray-500 text-xs py-1 w-20" x-text="getPrice(line.product_id)"></td>
                    <td class="text-right pl-2">
                      <button type="button" @click="form.items.splice(idx, 1)" class="text-red-500 hover:text-red-700 p-1">
                        <i data-lucide="x" class="w-4 h-4"></i>
                      </button>
                    </td>
                  </tr>
                </template>'''

if old_tr in content:
    content = content.replace(old_tr, new_tr)
    print("✅ Added 'Remove Line' button and fixed option values.")
else:
    print("⚠️ Could not find the exact table row. Trying regex...")
    # Fallback regex
    pattern = r'<template x-for="\(line, idx\) in form\.items" :key="idx">.*?</template>'
    content = re.sub(pattern, new_tr, content, flags=re.DOTALL)
    print("✅ Applied fix using regex.")

# ============================================================
# 3. Ensure the saveQuotation function filters out empty lines
# ============================================================
old_save_js = '''    async saveQuotation() {
      this.saving = true;
      try {
        const method = this.form.id ? 'PUT' : 'POST';
        const url = this.form.id ? `/sales/quotations/${this.form.id}/` : '/sales/quotations/';
        await apiFetch(url, { method: method, body: JSON.stringify(this.form) });'''

new_save_js = '''    async saveQuotation() {
      this.saving = true;
      try {
        // Filter out any empty lines (where no product is selected)
        const cleanItems = this.form.items.filter(i => i.product_id && i.quantity > 0);
        if (cleanItems.length === 0) {
          alert("Please add at least one product to the quotation.");
          this.saving = false;
          return;
        }

        const payload = { ...this.form, items: cleanItems };
        
        const method = this.form.id ? 'PUT' : 'POST';
        const url = this.form.id ? `/sales/quotations/${this.form.id}/` : '/sales/quotations/';
        await apiFetch(url, { method: method, body: JSON.stringify(payload) });'''

if old_save_js in content:
    content = content.replace(old_save_js, new_save_js)
    print("✅ Fixed saveQuotation to filter out empty lines.")

html_path.write_text(content, encoding="utf-8")

print("\n🎉 Done! Restart the server and hard refresh (Ctrl + Shift + R).")