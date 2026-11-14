import os
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
# 1. Update Cart Service (Apply Discount)
# ============================================================
cart_service = BACKEND_PATH / "sales" / "cart_service.py"
cart_content = cart_service.read_text(encoding="utf-8")

# Update totals calculation to include discount
old_totals = '''
    @staticmethod
    def totals(cart):
        sub = sum(Decimal(str(i.get("line_subtotal_net", 0))) for i in cart["items"])
        tax = sum(Decimal(str(i.get("tax_amount", 0))) for i in cart["items"])
        total = sum(Decimal(str(i.get("line_total", 0))) for i in cart["items"])
        
        return {"subtotal": float(sub), "tax_total": float(tax), "total": float(total),
                "item_count": len(cart["items"])}
'''

new_totals = '''
    @staticmethod
    def totals(cart):
        sub = sum(Decimal(str(i.get("line_subtotal_net", 0))) for i in cart["items"])
        tax = sum(Decimal(str(i.get("tax_amount", 0))) for i in cart["items"])
        gross = sum(Decimal(str(i.get("line_total", 0))) for i in cart["items"])
        
        discount = Decimal(str(cart.get("discount_amount", 0)))
        total = gross - discount
        
        return {"subtotal": float(sub), "tax_total": float(tax), "total": float(total),
                "discount_amount": float(discount), "item_count": len(cart["items"])}

    @staticmethod
    def apply_discount(tenant_id, branch_id, shift_id, discount_amount):
        cart = CartService.get(tenant_id, branch_id, shift_id)
        cart["discount_amount"] = float(discount_amount)
        CartService.save(tenant_id, branch_id, shift_id, cart)
        return cart
'''
patch_file(cart_service, old_totals, new_totals)

# Update checkout to save the discount to the Invoice
old_checkout = '''        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            total=totals["total"], status="PAID", payment_method=payment_method,
        )'''
new_checkout = '''        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_id=cart.get("customer_id"),
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            discount_total=totals.get("discount_amount", 0),
            total=totals["total"], status="PAID", payment_method=payment_method,
        )'''
patch_file(cart_service, old_checkout, new_checkout)
print("✅ Updated CartService for Discounts")

# ============================================================
# 2. Add Discount View (with RBAC check)
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
views_content = views_path.read_text(encoding="utf-8")

discount_view = '''
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def apply_cart_discount(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=400)
    
    discount_amount = float(request.data.get("discount_amount", 0))
    if discount_amount < 0:
        return Response({"error": "Invalid discount amount"}, status=400)

    # RBAC: Discounts over 100 require Manager/Owner
    if discount_amount > 100 and request.user.user_type not in ("TENANT_OWNER", "MANAGER", "SALES_ADMIN"):
        return Response({"error": "Discounts over K100 require Manager approval"}, status=403)

    cart = CartService.apply_discount(request.tenant.id, request.branch.id, shift.id, discount_amount)
    return Response({"success": True, "cart": {**cart, "totals": CartService.totals(cart)}})
'''

if "def apply_cart_discount" not in views_content:
    views_path.write_text(views_content + "\n\n" + discount_view, encoding="utf-8")

# Update URLs
urls_path = BACKEND_PATH / "sales" / "urls.py"
urls_content = urls_path.read_text(encoding="utf-8")
if "apply_cart_discount" not in urls_content:
    urls_content = urls_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("cart/discount/", views.apply_cart_discount, name="apply_cart_discount"),'
    )
    urls_path.write_text(urls_content, encoding="utf-8")
print("✅ Added apply_cart_discount endpoint")

# ============================================================
# 3. Update Frontend (POS UI)
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
html_content = pos_path.read_text(encoding="utf-8")

# Add Discount button next to Subtotal
old_subtotal_html = '''          <div class="flex justify-between text-sm">
            <span class="text-gray-500">Subtotal</span>
            <span x-text="formatCurrency(cart.totals.subtotal || 0)"></span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-500">VAT</span>
            <span x-text="formatCurrency(cart.totals.tax_total || 0)"></span>
          </div>'''

new_subtotal_html = '''          <div class="flex justify-between text-sm">
            <span class="text-gray-500">Subtotal</span>
            <span x-text="formatCurrency(cart.totals.subtotal || 0)"></span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-500">VAT</span>
            <span x-text="formatCurrency(cart.totals.tax_total || 0)"></span>
          </div>
          <div class="flex justify-between text-sm" x-show="cart.totals.discount_amount > 0">
            <span class="text-red-500">Discount</span>
            <span class="text-red-500" x-text="'- ' + formatCurrency(cart.totals.discount_amount || 0)"></span>
          </div>
          
          <div class="flex gap-2 mt-2">
            <button @click="openDiscountModal()" class="btn-secondary text-xs flex-1 py-1">Add Discount</button>
          </div>'''
patch_file(pos_path, old_subtotal_html, new_subtotal_html)

# Add Discount Modal
discount_modal = '''
    <!-- Discount Modal -->
    <div x-show="showDiscountModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-sm w-full p-6">
        <h2 class="text-xl font-bold mb-4">Apply Discount</h2>
        <form @submit.prevent="submitDiscount()" class="space-y-4">
          <div>
            <label class="block text-sm text-gray-500 mb-1">Discount Amount (K)</label>
            <input type="number" step="0.01" x-model="discountAmount" class="input-field text-lg font-bold" required>
            <p class="text-xs text-gray-500 mt-1">Note: Discounts over K100 require Manager approval.</p>
          </div>
          <div class="flex gap-2">
            <button type="button" @click="showDiscountModal = false" class="btn-secondary flex-1">Cancel</button>
            <button type="submit" class="btn-primary flex-1" :disabled="busy">Apply</button>
          </div>
        </form>
      </div>
    </div>
'''
html_content = html_content.replace('<!-- Receipt Modal -->', discount_modal + '\n    <!-- Receipt Modal -->')

# Add JS variables and functions
html_content = html_content.replace(
    "zReportModal: false,\n    zReportData: {},",
    "zReportModal: false, showDiscountModal: false, discountAmount: 0,\n    zReportData: {},"
)

js_functions = '''
    openDiscountModal() {
      if (!this.cart.items || this.cart.items.length === 0) {
        alert("Cart is empty"); return;
      }
      this.discountAmount = this.cart.totals.discount_amount || 0;
      this.showDiscountModal = true;
    },

    async submitDiscount() {
      this.busy = true;
      try {
        const res = await apiFetch('/sales/cart/discount/', {
          method: 'POST',
          body: JSON.stringify({ discount_amount: this.discountAmount })
        });
        this.cart = res.cart;
        this.showDiscountModal = false;
      } catch(e) {
        alert(e.response?.data?.error || e.message);
      } finally {
        this.busy = false;
      }
    },
'''
html_content = html_content.replace("    async openZReport() {", js_functions + "\n    async openZReport() {")

# Clear discount on checkout
html_content = html_content.replace(
    "this.customerName = ''; this.customerId = null;",
    "this.customerName = ''; this.customerId = null; this.discountAmount = 0;"
)
pos_path.write_text(html_content, encoding="utf-8")
print("✅ Updated POS UI with Discount Button and Modal")

# ============================================================
# 4. Update Receipt Template
# ============================================================
receipt_tpl = BACKEND_PATH / "templates" / "receipts" / "receipt.html"
r_content = receipt_tpl.read_text(encoding="utf-8")

old_totals_receipt = '''        <tr>
            <td>VAT (16%):</td>
            <td class="text-right">K{{ invoice.tax_total|floatformat:2 }}</td>
        </tr>
        <tr class="total-row">'''

new_totals_receipt = '''        <tr>
            <td>VAT (16%):</td>
            <td class="text-right">K{{ invoice.tax_total|floatformat:2 }}</td>
        </tr>
        {% if invoice.discount_total > 0 %}
        <tr>
            <td>Discount:</td>
            <td class="text-right text-red-600">-K{{ invoice.discount_total|floatformat:2 }}</td>
        </tr>
        {% endif %}
        <tr class="total-row">'''
patch_file(receipt_tpl, old_totals_receipt, new_totals_receipt)

# Also update the to_text receipt generator
receipt_service = BACKEND_PATH / "sales" / "receipt_service.py"
r_service_content = receipt_service.read_text(encoding="utf-8")
old_text_receipt = '''            f"{'VAT (16%):':<28}K{float(self.invoice.tax_total):>10.2f}",
            f"{'TOTAL:':<28}K{float(self.invoice.total):>10.2f}", '''
new_text_receipt = '''            f"{'VAT (16%):':<28}K{float(self.invoice.tax_total):>10.2f}",
            f"{'Discount:':<28}K{-float(self.invoice.discount_total):>10.2f}" if self.invoice.discount_total > 0 else "",
            f"{'TOTAL:':<28}K{float(self.invoice.total):>10.2f}", '''
patch_file(receipt_service, old_text_receipt, new_text_receipt)

print("✅ Updated Receipt templates to show discounts")
print("\n🎉 Done! Restart the server.")