import os
import re
import subprocess
import platform
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
# 1. Update Cart Service to Save Customer Phone
# ============================================================
cart_file = BACKEND_PATH / "sales" / "cart_service.py"
c_content = cart_file.read_text(encoding="utf-8")

old_invoice = '''        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_id=customer_id,
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            discount_total=totals.get("discount_amount", 0),
            total=totals["total"], status="PAID", payment_method=payment_method,
        )'''

new_invoice = '''        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_phone=cart.get("customer_phone", ""),
            customer_id=customer_id,
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            discount_total=totals.get("discount_amount", 0),
            total=totals["total"], status="PAID", payment_method=payment_method,
        )'''

c_content = c_content.replace(old_invoice, new_invoice)
cart_file.write_text(c_content, encoding="utf-8")
print("✅ Updated CartService to save Customer Phone")

# ============================================================
# 2. Update Sales View to Receive Customer Phone
# ============================================================
sales_views = BACKEND_PATH / "sales" / "views.py"
s_content = sales_views.read_text(encoding="utf-8")

old_cust_update = '''    customer_id = request.data.get("customer_id")
    customer_name = request.data.get("customer_name", "Cash Customer").strip()
        
    cart = CartService.get(request.tenant.id, request.branch.id, shift.id)
    
    if customer_id:
        from customers.models import Customer
        try:
            cust = Customer.objects.get(pk=customer_id, tenant=request.tenant)
            cart["customer_id"] = cust.id
            cart["customer_name"] = cust.full_name
        except Customer.DoesNotExist:
            pass
    else:
        cart["customer_id"] = None
        cart["customer_name"] = customer_name if customer_name else "Cash Customer"'''

new_cust_update = '''    customer_id = request.data.get("customer_id")
    customer_name = request.data.get("customer_name", "Cash Customer").strip()
    customer_phone = request.data.get("customer_phone", "").strip()
        
    cart = CartService.get(request.tenant.id, request.branch.id, shift.id)
    
    if customer_id:
        from customers.models import Customer
        try:
            cust = Customer.objects.get(pk=customer_id, tenant=request.tenant)
            cart["customer_id"] = cust.id
            cart["customer_name"] = cust.full_name
            cart["customer_phone"] = cust.phone_number
        except Customer.DoesNotExist:
            pass
    else:
        cart["customer_id"] = None
        cart["customer_name"] = customer_name if customer_name else "Cash Customer"
        cart["customer_phone"] = customer_phone'''

s_content = s_content.replace(old_cust_update, new_cust_update)
sales_views.write_text(s_content, encoding="utf-8")
print("✅ Updated Sales View to accept Customer Phone")

# ============================================================
# 3. Rebuild Receipt Service to print Address & Customer
# ============================================================
receipt_path = BACKEND_PATH / "sales" / "receipt_service.py"

new_receipt_code = '''
class ReceiptService:
    ESC, GS = "\\x1b", "\\x1d"

    def __init__(self, invoice):
        self.invoice = invoice

    def to_escpos(self, width=80):
        cpl = 32 if width == 58 else 42
        company = self.invoice.company
        
        lines = [self.ESC + "@", self.ESC + "a\\x01"] # Init & Center
        
        # Company Header
        lines.append(company.name + "\\n")
        if company.address:
            lines.append(company.address[:cpl] + "\\n")
        if company.phone:
            lines.append(f"Tel: {company.phone}\\n")
        lines.append(f"TPIN: {company.tpin}\\n")
        lines.append("-" * cpl + "\\n")
        
        # Invoice Details
        lines.append(self.ESC + "a\\x00") # Left align
        lines.append(f"Invoice: {self.invoice.invoice_number}\\n")
        lines.append(f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}\\n")
        
        # Customer Details
        if self.invoice.customer_name and self.invoice.customer_name != "Cash Customer":
            lines.append(f"Customer: {self.invoice.customer_name}\\n")
        if self.invoice.customer_phone:
            lines.append(f"Phone: {self.invoice.customer_phone}\\n")
            
        lines.append("-" * cpl + "\\n")
        
        # Items
        for item in self.invoice.items.all():
            name = item.product.name[:18]
            lines.append(f"{name:<20}{int(item.quantity):>3}{float(item.unit_price):>6.2f}{float(item.total):>8.2f}\\n")
            
        lines.extend([
            "-" * cpl + "\\n",
            f"{'Subtotal:':<25}K{float(self.invoice.subtotal):>10.2f}\\n",
            f"{'VAT (16%):':<25}K{float(self.invoice.tax_total):>10.2f}\\n",
        ])
        
        if getattr(self.invoice, 'discount_total', 0) > 0:
            lines.append(f"{'Discount:':<25}K{-float(self.invoice.discount_total):>10.2f}\\n")
            
        lines.extend([
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
        company = self.invoice.company
        
        lines = [
            "=" * 42, 
            company.name.center(42)
        ]
        
        if company.address:
            lines.append(company.address[:42].center(42))
        if company.phone:
            lines.append(f"Tel: {company.phone}".center(42))
            
        lines.append(f"TPIN: {company.tpin}".center(42))
        lines.append("=" * 42)
        
        lines.extend([
            f"Invoice: {self.invoice.invoice_number}",
            f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}"
        ])
        
        if self.invoice.customer_name and self.invoice.customer_name != "Cash Customer":
            lines.append(f"Customer: {self.invoice.customer_name}")
        if self.invoice.customer_phone:
            lines.append(f"Phone: {self.invoice.customer_phone}")
            
        lines.append("-" * 42)
        
        for item in self.invoice.items.all():
            lines.append(f"{item.product.name[:25]:<28}{float(item.quantity):>4.0f} x {float(item.unit_price):>7.2f} = {float(item.total):>8.2f}")
        
        lines.extend([
            "", 
            "-" * 42, 
            f"{'Subtotal:':<28}K{float(self.invoice.subtotal):>10.2f}",
            f"{'VAT (16%):':<28}K{float(self.invoice.tax_total):>10.2f}",
        ])
        
        if getattr(self.invoice, 'discount_total', 0) > 0:
            lines.append(f"{'Discount:':<28}K{-float(self.invoice.discount_total):>10.2f}")
            
        lines.extend([
            f"{'TOTAL:':<28}K{float(self.invoice.total):>10.2f}", 
            "=" * 42
        ])
        
        if self.invoice.zra_validation_code:
            lines.append(f"ZRA Code: {self.invoice.zra_validation_code}")
            
        return "\\n".join(lines)
'''
receipt_path.write_text(new_receipt_code.strip(), encoding="utf-8")
print("✅ Rebuilt ReceiptService to include Address and Customer Details")

# ============================================================
# 4. Update POS Frontend to send Customer Phone
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
p_content = pos_path.read_text(encoding="utf-8")

# Add customerPhone state
p_content = p_content.replace(
    "customerSearch: '', customerResults: [], showCustDropdown: false, showNewCustModal: false,",
    "customerSearch: '', customerResults: [], showCustDropdown: false, showNewCustModal: false, customerPhone: '',"
)

# Update selectCustomer
p_content = p_content.replace(
    "      this.customerId = c.id;\n      this.customerName = c.name;",
    "      this.customerId = c.id;\n      this.customerName = c.name;\n      this.customerPhone = c.phone;"
)

# Update clearCustomer
p_content = p_content.replace(
    "      this.customerId = null;\n      this.customerName = '';",
    "      this.customerId = null;\n      this.customerName = '';\n      this.customerPhone = '';"
)

# Update updateCustomer API call
p_content = p_content.replace(
    "body: JSON.stringify({ customer_id: this.customerId, customer_name: this.customerName })",
    "body: JSON.stringify({ customer_id: this.customerId, customer_name: this.customerName, customer_phone: this.customerPhone })"
)

# Clear customerPhone on checkout success
p_content = p_content.replace(
    "this.customerName = ''; this.customerId = null; this.paymentPhone = '';",
    "this.customerName = ''; this.customerId = null; this.customerPhone = ''; this.paymentPhone = '';"
)

pos_path.write_text(p_content, encoding="utf-8")
print("✅ Updated POS UI to pass Customer Phone")

print("\n🎉 Done! Restart the server.")