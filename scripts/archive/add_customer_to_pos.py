import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def patch_file(path, pattern, replacement, is_regex=False):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if is_regex:
        new_content, count = re.subn(pattern, replacement, content, flags=re.DOTALL)
    else:
        if pattern not in content:
            print(f"  ❌ Pattern not found in {path.name}")
            return
        new_content = content.replace(pattern, replacement)
        count = 1
        
    if count > 0:
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(new_content)
        print(f"  ✅ Patched {path.name}")
    else:
        print(f"  ❌ Regex failed in {path.name}")

# ============================================================
# 1. Update Backend Receipt Service (Print Customer if not Cash Customer)
# ============================================================
print("1. Updating Receipt Service...")
receipt_file = BACKEND_PATH / "sales" / "receipt_service.py"

new_receipt_text = '''    def to_text(self):
        lines = [
            "=" * 42, self.invoice.company.name.center(42),
            f"TPIN: {self.invoice.company.tpin}".center(42), "=" * 42,
            f"Invoice: {self.invoice.invoice_number}",
            f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}",
        ]
        
        # Add Customer Name if it exists and is not the default
        if self.invoice.customer_name and self.invoice.customer_name != "Cash Customer":
            lines.append(f"Customer: {self.invoice.customer_name}")
            
        lines.append("-" * 42)
        
        for item in self.invoice.items.all():
            lines.append(f"{item.product.name[:25]:<28}{float(item.quantity):>4.0f} x {float(item.unit_price):>7.2f} = {float(item.total):>8.2f}")
        
        lines.extend([
            "", 
            "-" * 42, 
            f"{'Subtotal:':<28}K{float(self.invoice.subtotal):>10.2f}",
            f"{'VAT (16%):':<28}K{float(self.invoice.tax_total):>10.2f}",
            f"{'TOTAL:':<28}K{float(self.invoice.total):>10.2f}", 
            "=" * 42
        ])
        
        if self.invoice.zra_validation_code:
            lines.append(f"ZRA Code: {self.invoice.zra_validation_code}")
            
        return "\\n".join(lines)'''

pattern_text = r"    def to_text\(self\):.*?return \"\\n\"\.join\(lines\)"
patch_file(receipt_file, pattern_text, new_receipt_text, is_regex=True)


# ============================================================
# 2. Add Backend View to Update Cart Customer
# ============================================================
print("\n2. Adding Cart Customer Endpoint...")
views_file = BACKEND_PATH / "sales" / "views.py"

new_view = '''
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_cart_customer(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=400)
    
    customer_name = request.data.get("customer_name", "Cash Customer").strip()
    if not customer_name:
        customer_name = "Cash Customer"
        
    cart = CartService.get(request.tenant.id, request.branch.id, shift.id)
    cart["customer_name"] = customer_name
    CartService.save(request.tenant.id, request.branch.id, shift.id, cart)
    
    return Response({"success": True, "customer_name": customer_name})
'''

with open(views_file, "a", encoding="utf-8") as f:
    f.write("\n" + new_view.strip() + "\n")
print("  ✅ Appended update_cart_customer to views.py")

# Add URL route
urls_file = BACKEND_PATH / "sales" / "urls.py"
patch_file(
    urls_file, 
    'path("cart/clear/", views.cart_clear, name="cart_clear"),',
    'path("cart/clear/", views.cart_clear, name="cart_clear"),\n    path("cart/customer/", views.update_cart_customer, name="update_cart_customer"),'
)


# ============================================================
# 3. Add Frontend UI to POS
# ============================================================
print("\n3. Updating POS Frontend...")
pos_file = BACKEND_PATH / "templates" / "pos" / "pos.html"

# A. Add HTML input field below the "Cart" header
html_patch_old = '''        <div class="p-4 border-b flex justify-between items-center">
          <h2 class="font-semibold">Cart (<span x-text="cart.totals.item_count || 0"></span>)</h2>
          <button x-show="cart.items?.length > 0" @click="clearCart()" class="text-xs text-red-600">Clear</button>
        </div>'''
html_patch_new = '''        <div class="p-4 border-b flex justify-between items-center">
          <h2 class="font-semibold">Cart (<span x-text="cart.totals.item_count || 0"></span>)</h2>
          <button x-show="cart.items?.length > 0" @click="clearCart()" class="text-xs text-red-600">Clear</button>
        </div>
        <div class="px-4 py-2 border-b bg-gray-50">
          <input type="text" x-model="customerName" @change="updateCustomer()" placeholder="Customer Name (Optional)" class="w-full px-2 py-1 text-sm border rounded">
        </div>'''
patch_file(pos_file, html_patch_old, html_patch_new)

# B. Add customerName state and updateCustomer JS function
js_patch_old = '''    shift: null, products: [], cart: { items: [], totals: {} },
    search: '', busy: false, lastScan: null,'''
js_patch_new = '''    shift: null, products: [], cart: { items: [], totals: {} },
    search: '', busy: false, lastScan: null, customerName: '','''
patch_file(pos_file, js_patch_old, js_patch_new)

# C. Add the updateCustomer method
js_method_patch_old = '''    async clearCart() {
      if (!confirm('Clear cart?')) return;'''
js_method_patch_new = '''    async updateCustomer() {
      if (!this.shift) return;
      try {
        await apiFetch('/sales/cart/customer/', {
          method: 'POST',
          body: JSON.stringify({ customer_name: this.customerName })
        });
      } catch (e) { console.error('Failed to update customer', e); }
    },

    async clearCart() {
      if (!confirm('Clear cart?')) return;'''
patch_file(pos_file, js_method_patch_old, js_method_patch_new)

# D. Clear customer name after successful checkout
js_checkout_patch_old = '''        this.receiptModal = { ...res, text: receipt.text };
        this.cart = { items: [], totals: {} };
        this.checkoutOpen = false;'''
js_checkout_patch_new = '''        this.receiptModal = { ...res, text: receipt.text };
        this.cart = { items: [], totals: {} };
        this.customerName = '';
        this.checkoutOpen = false;'''
patch_file(pos_file, js_checkout_patch_old, js_checkout_patch_new)

print("\n🎉 Done! Run 'python manage.py runserver' and test a new sale.")