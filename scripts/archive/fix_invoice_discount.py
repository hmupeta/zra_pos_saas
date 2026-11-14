import os
import re
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add discount_total to Invoice Model
# ============================================================
models_path = BACKEND_PATH / "sales" / "models.py"
m_content = models_path.read_text(encoding="utf-8")

if "discount_total =" not in m_content:
    m_content = m_content.replace(
        "tax_total = models.DecimalField(max_digits=10, decimal_places=2)",
        "tax_total = models.DecimalField(max_digits=10, decimal_places=2)\n    discount_total = models.DecimalField(max_digits=10, decimal_places=2, default=0)"
    )
    models_path.write_text(m_content, encoding="utf-8")
    print("✅ Added discount_total to Invoice model")

# ============================================================
# 2. Update Cart Checkout to Save Discount
# ============================================================
cart_path = BACKEND_PATH / "sales" / "cart_service.py"
c_content = cart_path.read_text(encoding="utf-8")

# Replace the Invoice.objects.create block to include discount_total
old_create = '''        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_id=customer_id,
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            total=totals["total"], status="PAID", payment_method=payment_method,
        )'''

new_create = '''        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_id=customer_id,
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            discount_total=totals.get("discount_amount", 0),
            total=totals["total"], status="PAID", payment_method=payment_method,
        )'''

c_content = c_content.replace(old_create, new_create)
cart_path.write_text(c_content, encoding="utf-8")
print("✅ Updated Cart Checkout to save discount_total")

# ============================================================
# 3. Update Receipt Service to be Bulletproof
# ============================================================
receipt_path = BACKEND_PATH / "sales" / "receipt_service.py"
r_content = receipt_path.read_text(encoding="utf-8")

# Replace the broken discount line with a safe getattr check
old_line = 'f"{\'Discount:\':<28}K{-float(self.invoice.discount_total):>10.2f}" if self.invoice.discount_total > 0 else "",'
new_line = 'f"{\'Discount:\':<28}K{-float(getattr(self.invoice, \'discount_total\', 0)):>10.2f}" if getattr(self.invoice, \'discount_total\', 0) > 0 else "",'

if old_line in r_content:
    r_content = r_content.replace(old_line, new_line)
    receipt_path.write_text(r_content, encoding="utf-8")
    print("✅ Hardened receipt_service.py against missing discount_total")
else:
    # If regex is needed due to slight syntax differences
    r_content = re.sub(r'if self\.invoice\.discount_total > 0 else ""', 'if getattr(self.invoice, "discount_total", 0) > 0 else ""', r_content)
    receipt_path.write_text(r_content, encoding="utf-8")
    print("✅ Hardened receipt_service.py using regex")

# ============================================================
# 4. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "sales"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")