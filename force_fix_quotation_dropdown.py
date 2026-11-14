import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "quotations.html"

content = html_path.read_text(encoding="utf-8")

# ============================================================
# 1. Fix the HTML <select> generation
# ============================================================
# We use String() for both the model and the option value to guarantee they match
old_select = '''                    <td class="pr-2">
                      <select x-model="line.product_id" class="input-field text-sm py-1" required>
                        <option value="">Select Product...</option>
                        <template x-for="p in products" :key="p.id">
                          <option :value="String(p.id)" x-text="p.name + ' (' + formatCurrency(p.selling_price) + ')'"></option>
                        </template>
                      </select>
                    </td>'''

new_select = '''                    <td class="pr-2">
                      <select x-model="line.product_id" class="input-field text-sm py-1" required>
                        <option value="" disabled>-- Select Product --</option>
                        <template x-for="p in products" :key="p.id">
                          <option :value="String(p.id)" x-text="p.name + ' (' + formatCurrency(p.selling_price) + ')'"></option>
                        </template>
                      </select>
                    </td>'''

if old_select in content:
    content = content.replace(old_select, new_select)
    print("✅ Updated <select> option binding in HTML.")

# ============================================================
# 2. Fix the editQuote JS function to ensure products are loaded first
# ============================================================
old_edit_js = '''    async editQuote(id) {
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

new_edit_js = '''    async editQuote(id) {
      try {
        // 1. Fetch the quotation details
        const q = await apiFetch(`/sales/quotations/${id}/`);
        
        // 2. Ensure products are loaded before opening the modal
        if (!this.products || this.products.length === 0) {
          this.products = await apiFetch('/inventory/products/');
        }

        // 3. Map the items, forcing both IDs to be strings
        const mappedItems = q.items.map(i => ({
          product_id: String(i.product_id), 
          quantity: i.quantity
        }));

        // 4. Set the form state
        this.form = {
          id: q.id, 
          customer_id: q.customer_id ? String(q.customer_id) : '', 
          customer_name: q.customer, 
          valid_until: q.valid_until,
          items: mappedItems
        };
        
        this.showModal = true;
        
        // 5. Force Alpine to re-evaluate the select elements
        this.$nextTick(() => {
          if(window.lucide) lucide.createIcons();
        });
        
      } catch(e) { 
        alert('Error loading quotation: ' + e.message); 
      }
    },'''

if old_edit_js in content:
    content = content.replace(old_edit_js, new_edit_js)
    print("✅ Updated editQuote JS to wait for products and force string matching.")
else:
    print("⚠️ Could not find the exact editQuote function. Checking for variations.")
    # Fallback regex
    pattern = r"async editQuote\(id\) \{.*?\}\s*\},"
    content = re.sub(pattern, new_edit_js.strip(), content, flags=re.DOTALL)
    print("✅ Applied fix using regex.")

html_path.write_text(content, encoding="utf-8")
print("\n🎉 Done! Restart the server and hard refresh the Quotations page.")