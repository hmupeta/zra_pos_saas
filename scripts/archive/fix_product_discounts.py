import os
import subprocess
import platform
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def patch_file(path, old, new, is_regex=False):
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if is_regex:
        content = re.sub(old, new, content, flags=re.DOTALL)
    else:
        content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")

# ============================================================
# 1. Update Product Model
# ============================================================
models_path = BACKEND_PATH / "inventory" / "models.py"
content = models_path.read_text(encoding="utf-8")

if "discount_percentage" not in content:
    content = content.replace(
        "selling_price = models.DecimalField(max_digits=10, decimal_places=2)",
        "selling_price = models.DecimalField(max_digits=10, decimal_places=2)\n    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Auto-applied discount %')\n    "
    )
    models_path.write_text(content, encoding="utf-8")
print("✅ Added discount_percentage to Product model")

# ============================================================
# 2. Update Inventory Views (Save & Return Discount)
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Update product list to include discount
v_content = v_content.replace(
    '"selling_price": float(p.selling_price),',
    '"selling_price": float(p.selling_price),\n                "discount_percentage": float(p.discount_percentage),'
)

# Update product creation to save discount
v_content = v_content.replace(
    'selling_price=Decimal(str(data.get("selling_price", 0))),',
    'selling_price=Decimal(str(data.get("selling_price", 0))),\n            discount_percentage=Decimal(str(data.get("discount_percentage", 0))),'
)
views_path.write_text(v_content, encoding="utf-8")
print("✅ Updated inventory/views.py to handle product discounts")

# ============================================================
# 3. Update Cart Service (Auto-apply product discount)
# ============================================================
cart_service = BACKEND_PATH / "sales" / "cart_service.py"
c_content = cart_service.read_text(encoding="utf-8")

# We need to replace the entire add_item method to handle the discount before VAT calculation
new_add_item = '''    @staticmethod
    def add_item(tenant_id, branch_id, shift_id, product_data, quantity=1):
        cart = CartService.get(tenant_id, branch_id, shift_id)
        qty = Decimal(str(quantity))
        
        existing = next((i for i in cart["items"] if i["barcode"] == product_data["barcode"]), None)
        
        original_price = Decimal(str(product_data["selling_price"]))
        discount_pct = Decimal(str(product_data.get("discount_percentage", 0)))
        
        # Calculate discounted price
        if discount_pct > 0:
            discount_amt = original_price * (discount_pct / 100)
            price_gross = original_price - discount_amt
        else:
            price_gross = original_price
            
        tax_rate = Decimal(str(product_data["tax_rate"]))
        
        if existing:
            new_qty = Decimal(str(existing["quantity"])) + qty
            existing["quantity"] = float(new_qty)
            
            # Recalculate totals
            line_total_gross = new_qty * price_gross
            line_subtotal_net = line_total_gross / (1 + (tax_rate / 100))
            line_tax = line_total_gross - line_subtotal_net
            
            existing["line_total"] = float(line_total_gross)
            existing["line_subtotal_net"] = float(line_subtotal_net)
            existing["tax_amount"] = float(line_tax)
        else:
            line_total_gross = qty * price_gross
            line_subtotal_net = line_total_gross / (1 + (tax_rate / 100))
            line_tax = line_total_gross - line_subtotal_net
            
            cart["items"].append({
                "product_id": product_data["id"],
                "barcode": product_data["barcode"],
                "name": product_data["name"],
                "quantity": float(qty),
                "unit_price": float(original_price),
                "price_gross": float(price_gross),
                "discount_percentage": float(discount_pct),
                "tax_rate": float(tax_rate),
                "line_subtotal_net": float(line_subtotal_net),
                "tax_amount": float(line_tax),
                "line_total": float(line_total_gross),
                "zra_item_code": product_data.get("zra_item_code", ""),
            })
            
        CartService.save(tenant_id, branch_id, shift_id, cart)
        return cart
'''
c_content = re.sub(r"    @staticmethod\n    def add_item\(tenant_id, branch_id, shift_id, product_data, quantity=1\):.*?return cart", new_add_item.strip(), c_content, flags=re.DOTALL)
cart_service.write_text(c_content, encoding="utf-8")
print("✅ Updated CartService to auto-apply discounts")

# ============================================================
# 4. Update Products UI (Add Discount % field)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"
h_content = html_path.read_text(encoding="utf-8")

# Add column to table header
h_content = h_content.replace(
    '<th class="px-4 py-3 text-right">Selling</th>',
    '<th class="px-4 py-3 text-right">Selling</th>\n            <th class="px-4 py-3 text-center">Discount</th>'
)

# Add column to table row
h_content = h_content.replace(
    '<td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(p.selling_price)"></td>',
    '<td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(p.selling_price)"></td>\n              <td class="px-4 py-3 text-center">\n                <span x-show="p.discount_percentage > 0" class="bg-red-100 text-red-700 px-2 py-0.5 rounded text-xs font-bold" x-text="p.discount_percentage + \'%\'"></span>\n                <span x-show="p.discount_percentage === 0" class="text-gray-400 text-xs">-</span>\n              </td>'
)

# Add discount input to the New Product form
h_content = h_content.replace(
    '''              <div>
                <label class="block text-xs text-gray-500 mb-1">Selling Price</label>
                <input type="number" step="0.01" x-model="form.selling_price" class="input-field" required>
              </div>''',
    '''              <div>
                <label class="block text-xs text-gray-500 mb-1">Selling Price</label>
                <input type="number" step="0.01" x-model="form.selling_price" class="input-field" required>
              </div>
            </div>
            
            <div class="grid grid-cols-2 gap-3">
              <div>
                <label class="block text-xs text-gray-500 mb-1">Discount % (Manager Only)</label>
                <input type="number" step="0.01" x-model="form.discount_percentage" class="input-field" placeholder="0.00">
              </div>'''
)

# Initialize discount in form state
h_content = h_content.replace(
    "form: { barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', current_stock: 0, reorder_level: 10 },",
    "form: { barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', discount_percentage: 0, current_stock: 0, reorder_level: 10 },"
)
h_content = h_content.replace(
    "this.form = { barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', current_stock: 0, reorder_level: 10 };",
    "this.form = { barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', discount_percentage: 0, current_stock: 0, reorder_level: 10 };"
)

html_path.write_text(h_content, encoding="utf-8")
print("✅ Updated Products UI with Discount field")

# ============================================================
# 5. Update POS UI (Remove Manual Discount, Show Auto-Discount)
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
p_content = pos_path.read_text(encoding="utf-8")

# Remove the manual discount button
p_content = p_content.replace(
    '''          <div class="flex gap-2 mt-2">
            <button @click="openDiscountModal()" class="btn-secondary text-xs flex-1 py-1">Add Discount</button>
          </div>''',
    ''
)

# Update the cart item display to show the discounted price beautifully
old_cart_item = '''              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate" x-text="item.name"></div>
                <div class="text-xs text-gray-500">
                  <span x-text="formatCurrency(item.unit_price)"></span> × <span x-text="item.quantity"></span>
                </div>
              </div>'''

new_cart_item = '''              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate" x-text="item.name"></div>
                <div class="text-xs text-gray-500">
                  <template x-if="item.discount_percentage > 0">
                    <span>
                      <span class="line-through text-gray-400" x-text="formatCurrency(item.unit_price)"></span>
                      <span class="text-red-600 font-bold ml-1" x-text="formatCurrency(item.price_gross)"></span>
                    </span>
                  </template>
                  <template x-if="item.discount_percentage === 0">
                    <span x-text="formatCurrency(item.unit_price)"></span>
                  </template>
                  × <span x-text="item.quantity"></span>
                </div>
              </div>'''
p_content = p_content.replace(old_cart_item, new_cart_item)

pos_path.write_text(p_content, encoding="utf-8")
print("✅ Updated POS UI (Removed manual discount button)")

# ============================================================
# 6. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "inventory"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")