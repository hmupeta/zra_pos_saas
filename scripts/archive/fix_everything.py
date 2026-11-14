from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Rebuild receipt_service.py from scratch (Fixes SyntaxError)
# ============================================================
receipt_file = BACKEND_PATH / "sales" / "receipt_service.py"
correct_code = '''
class ReceiptService:
    ESC, GS = "\\x1b", "\\x1d"

    def __init__(self, invoice):
        self.invoice = invoice

    def to_escpos(self, width=80):
        cpl = 32 if width == 58 else 42
        lines = [
            self.ESC + "@",
            self.ESC + "a\\x01",
            self.invoice.company.name + "\\n",
            self.ESC + "a\\x00",
            self.invoice.company.address[:cpl] + "\\n",
            f"TPIN: {self.invoice.company.tpin}\\n",
            "-" * cpl + "\\n",
            f"Invoice: {self.invoice.invoice_number}\\n",
            f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}\\n",
        ]
        
        if self.invoice.customer_name and self.invoice.customer_name != "Cash Customer":
            lines.append(f"Customer: {self.invoice.customer_name}\\n")
            
        lines.append("-" * cpl + "\\n")
        
        for item in self.invoice.items.all():
            lines.append(f"{item.product.name[:18]:<20}{int(item.quantity):>3}{float(item.unit_price):>6.2f}{float(item.total):>8.2f}\\n")
            
        lines.extend([
            "-" * cpl + "\\n",
            f"{'Subtotal:':<25}K{float(self.invoice.subtotal):>10.2f}\\n",
            f"{'VAT (16%):':<25}K{float(self.invoice.tax_total):>10.2f}\\n",
            "-" * cpl + "\\n",
            self.ESC + "!\\x10",
            f"{'TOTAL:':<25}K{float(self.invoice.total):>10.2f}\\n",
            self.ESC + "!\\x00",
            "-" * cpl + "\\n",
        ])
        
        if self.invoice.zra_validation_code:
            lines.append(self.ESC + "a\\x01")
            lines.append("ZRA SMART INVOICE\\n")
            lines.append(f"Code: {self.invoice.zra_validation_code}\\n")
            lines.append(self.ESC + "a\\x00")
            
        lines.append("\\n")
        lines.append(self.ESC + "a\\x01")
        lines.append("Thank you for your business!\\n")
        lines.append("\\n\\n\\n")
        lines.append(self.GS + "V\\x42\\x00")
        
        return "".join(lines).encode("latin-1", errors="replace")

    def to_text(self):
        lines = [
            "=" * 42, self.invoice.company.name.center(42),
            f"TPIN: {self.invoice.company.tpin}".center(42), "=" * 42,
            f"Invoice: {self.invoice.invoice_number}",
            f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}",
        ]
        
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
            
        return "\\n".join(lines)
'''
receipt_file.write_text(correct_code.strip(), encoding="utf-8")
print("✅ Rebuilt sales/receipt_service.py (Fixed syntax & added Customer/VAT)")

# ============================================================
# 2. Safely Patch pos.html for Customer Name Input
# ============================================================
pos_file = BACKEND_PATH / "templates" / "pos" / "pos.html"
html_content = pos_file.read_text(encoding="utf-8")

# Add Customer Input Field
search_cart_header = """          <button x-show="cart.items?.length > 0" @click="clearCart()" class="text-xs text-red-600">Clear</button>
        </div>"""

replace_cart_header = """          <button x-show="cart.items?.length > 0" @click="clearCart()" class="text-xs text-red-600">Clear</button>
        </div>
        <div class="px-4 py-2 border-b bg-gray-50">
          <input type="text" x-model="customerName" @change="updateCustomer()" placeholder="Customer Name (Optional)" class="w-full px-2 py-1 text-sm border rounded">
        </div>"""

if 'placeholder="Customer Name (Optional)"' not in html_content:
    html_content = html_content.replace(search_cart_header, replace_cart_header)
    print("✅ Added Customer Name input to POS HTML")
else:
    print("✅ Customer Name input already exists in POS HTML")

# Add JS variables and functions
if "customerName: ''" not in html_content:
    html_content = html_content.replace(
        "search: '', busy: false, lastScan: null,",
        "search: '', busy: false, lastScan: null, customerName: '',"
    )

if "async updateCustomer()" not in html_content:
    js_methods = """    async updateCustomer() {
      if (!this.shift) return;
      try {
        await apiFetch('/sales/cart/customer/', {
          method: 'POST',
          body: JSON.stringify({ customer_name: this.customerName })
        });
      } catch (e) { console.error('Failed to update customer', e); }
    },

    async clearCart() {"""
    html_content = html_content.replace("    async clearCart() {", js_methods)

# Clear input after checkout
if "this.customerName = '';" not in html_content:
    html_content = html_content.replace(
        "this.cart = { items: [], totals: {} };\n        this.checkoutOpen = false;",
        "this.cart = { items: [], totals: {} };\n        this.customerName = '';\n        this.checkoutOpen = false;"
    )

pos_file.write_text(html_content, encoding="utf-8")
print("✅ Updated pos.html logic for Customer Name")

print("\n🎉 Done! Run 'python manage.py runserver' and test.")