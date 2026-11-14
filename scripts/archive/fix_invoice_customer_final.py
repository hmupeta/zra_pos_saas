import os
import re
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Force the model to have the customer field
# ============================================================
models_path = BACKEND_PATH / "sales" / "models.py"
content = models_path.read_text(encoding="utf-8")

# If the field is missing, inject it
if "customer = models.ForeignKey" not in content:
    # We use regex to safely find the Invoice class and add the field
    pattern = r"(class Invoice\(models\.Model\):[\s\S]*?)(customer_name = models\.CharField)"
    replacement = r"\1customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True)\n    \2"
    
    content = re.sub(pattern, replacement, content, count=1)
    models_path.write_text(content, encoding="utf-8")
    print("✅ Injected 'customer' field into Invoice model")
else:
    print("✅ Invoice model already has 'customer' field")

# ============================================================
# 2. Fix the Cart Service to handle missing customer safely
# ============================================================
cart_service = BACKEND_PATH / "sales" / "cart_service.py"
c_content = cart_service.read_text(encoding="utf-8")

# Replace the whole Invoice.objects.create block to be bulletproof
# We use a regex to match the create block
pattern = r"        invoice = Invoice\.objects\.create\([\s\S]*?\)"
replacement = '''        # Safely handle customer (allow null for walk-in customers)
        cid = cart.get("customer_id")
        if not cid or cid == "":
            cid = None

        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_id=cid,
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            total=totals["total"], status="PAID", payment_method=payment_method,
        )'''

c_content = re.sub(pattern, replacement, c_content, count=1, flags=re.DOTALL)
cart_service.write_text(c_content, encoding="utf-8")
print("✅ Updated Cart checkout to safely handle walk-in customers")

# ============================================================
# 3. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "sales"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")