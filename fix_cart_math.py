from pathlib import Path
import re

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Fix the Cart Calculation Logic in cart_service.py
# ============================================================
cart_file = BACKEND_PATH / "sales" / "cart_service.py"
cart_content = cart_file.read_text(encoding="utf-8")

# We will replace the add_item method entirely to ensure correct math
new_add_item = '''    @staticmethod
    def add_item(tenant_id, branch_id, shift_id, product_data, quantity=1):
        cart = CartService.get(tenant_id, branch_id, shift_id)
        qty = Decimal(str(quantity))
        
        existing = next((i for i in cart["items"] if i["barcode"] == product_data["barcode"]), None)
        
        if existing:
            new_qty = Decimal(str(existing["quantity"])) + qty
            existing["quantity"] = float(new_qty)
            
            # FIX: Recalculate line totals based on the new quantity
            price = Decimal(str(existing["unit_price"]))
            tax_rate = Decimal(str(existing["tax_rate"]))
            line_sub = new_qty * price
            line_tax = line_sub * tax_rate / 100
            
            existing["line_total"] = float(line_sub)
            existing["tax_amount"] = float(line_tax)
        else:
            price = Decimal(str(product_data["selling_price"]))
            tax_rate = Decimal(str(product_data["tax_rate"]))
            line_sub = qty * price
            line_tax = line_sub * tax_rate / 100
            
            cart["items"].append({
                "product_id": product_data["id"],
                "barcode": product_data["barcode"],
                "name": product_data["name"],
                "quantity": float(qty),
                "unit_price": float(price),
                "tax_rate": float(tax_rate),
                "tax_amount": float(line_tax),
                "line_total": float(line_sub),
                "zra_item_code": product_data.get("zra_item_code", ""),
            })
            
        CartService.save(tenant_id, branch_id, shift_id, cart)
        return cart
'''

# Regex to replace the add_item method
pattern = r"    @staticmethod\n    def add_item\(tenant_id, branch_id, shift_id, product_data, quantity=1\):.*?return cart"
cart_content = re.sub(pattern, new_add_item, cart_content, flags=re.DOTALL)
cart_file.write_text(cart_content, encoding="utf-8")
print("✅ Fixed Cart Math in sales/cart_service.py")


# ============================================================
# 2. Fix the Duplicate Customer Input in pos.html
# ============================================================
pos_file = BACKEND_PATH / "templates" / "pos" / "pos.html"
html_content = pos_file.read_text(encoding="utf-8")

# Find the entire right-hand cart sidebar block and replace it cleanly
new_cart_html = '''
      <!-- Cart -->
      <div class="w-96 bg-white border-l flex flex-col">
        <div class="p-4 border-b flex justify-between items-center">
          <h2 class="font-semibold">Cart (<span x-text="cart.totals.item_count || 0"></span>)</h2>
          <button x-show="cart.items?.length > 0" @click="clearCart()" class="text-xs text-red-600">Clear</button>
        </div>
        
        <!-- Customer Name Input (ONLY ONE) -->
        <div class="px-4 py-2 border-b bg-gray-50">
          <input type="text" x-model="customerName" @change="updateCustomer()" placeholder="Customer Name (Optional)" class="w-full px-2 py-1 text-sm border rounded">
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-2">
          <template x-if="!cart.items || cart.items.length === 0">
            <div class="text-center py-12 text-gray-400">Scan or click products</div>
          </template>
          <template x-for="item in cart.items || []" :key="item.barcode">
            <div class="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate" x-text="item.name"></div>
                <div class="text-xs text-gray-500">
                  <span x-text="formatCurrency(item.unit_price)"></span> × <span x-text="item.quantity"></span>
                </div>
              </div>
              <div class="text-sm font-semibold" x-text="formatCurrency(item.line_total)"></div>
            </div>
          </template>
        </div>

        <div class="p-4 border-t space-y-3">
          <div class="flex justify-between text-sm">
            <span class="text-gray-500">Subtotal</span>
            <span x-text="formatCurrency(cart.totals.subtotal || 0)"></span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-500">VAT</span>
            <span x-text="formatCurrency(cart.totals.tax_total || 0)"></span>
          </div>
          <div class="flex justify-between text-lg font-bold pt-2 border-t">
            <span>Total</span>
            <span class="text-brand-700" x-text="formatCurrency(cart.totals.total || 0)"></span>
          </div>
          <button :disabled="!shift || !cart.items || cart.items.length === 0"
                  @click="checkoutOpen = true" class="btn-primary w-full py-3 text-base">
            Checkout
          </button>
          <button x-show="shift" @click="closeShift()" class="btn-secondary w-full text-sm">
            Close Shift
          </button>
        </div>
      </div>
'''

# Replace the old cart block with the new clean one
pattern_cart = r"      <!-- Cart -->.*?      </div>\n    </div>"
html_content = re.sub(pattern_cart, new_cart_html + "\n    </div>", html_content, flags=re.DOTALL)
pos_file.write_text(html_content, encoding="utf-8")
print("✅ Cleaned up POS HTML (removed duplicate input, ensured correct UI layout)")

print("\n🎉 Done! Restart the server and clear your cart to test.")