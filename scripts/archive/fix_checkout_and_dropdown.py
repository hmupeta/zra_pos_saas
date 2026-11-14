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
# 1. Fix Sales Models (Ensure Customer field exists)
# ============================================================
models_path = BACKEND_PATH / "sales" / "models.py"
m_content = models_path.read_text(encoding="utf-8")

if "customer = models.ForeignKey" not in m_content:
    m_content = m_content.replace(
        "customer_name = models.CharField(max_length=200, default='Cash Customer')",
        "customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True)\n    customer_name = models.CharField(max_length=200, default='Cash Customer')"
    )
    models_path.write_text(m_content, encoding="utf-8")
    print("✅ Added customer field to Invoice model")

# ============================================================
# 2. Fix Cart Checkout (Safely pass customer_id)
# ============================================================
cart_service = BACKEND_PATH / "sales" / "cart_service.py"
c_content = cart_service.read_text(encoding="utf-8")

# Replace the Invoice.objects.create call to use customer_id properly
old_create = '''        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_id=cart.get("customer_id"),
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            total=totals["total"], status="PAID", payment_method=payment_method,
        )'''

new_create = '''        # Safely handle customer relation
        customer_id = cart.get("customer_id")
        
        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_id=customer_id if customer_id else None,
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            total=totals["total"], status="PAID", payment_method=payment_method,
        )'''
c_content = c_content.replace(old_create, new_create)
cart_service.write_text(c_content, encoding="utf-8")
print("✅ Fixed Cart checkout customer assignment")

# ============================================================
# 3. Fix POS Dropdown (Ensure it loads correctly)
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
p_content = pos_path.read_text(encoding="utf-8")

# Update load logic to grab ALL configured gateways for the branch
old_load = '''        // Load payment gateways for this branch
        this.paymentConfigs = await apiFetch('/payments/configs/');
        // Filter only Mobile Money providers
        this.availableMomoProviders = this.paymentConfigs
          .filter(c => c.provider.includes('DIRECT'))
          .map(c => c.provider);
          
        if (this.availableMomoProviders.length > 0) {
          this.selectedProvider = this.availableMomoProviders[0];
        }'''

new_load = '''        // Load payment gateways for this branch
        try {
          this.paymentConfigs = await apiFetch('/payments/configs/');
          
          // Get unique providers that are Mobile Money
          const momoConfigs = this.paymentConfigs.filter(c => ['MTN_DIRECT', 'AIRTEL_DIRECT', 'ZAMTEL_DIRECT'].includes(c.provider));
          this.availableMomoProviders = [...new Set(momoConfigs.map(c => c.provider))];
          
          if (this.availableMomoProviders.length > 0) {
            this.selectedProvider = this.availableMomoProviders[0];
          }
        } catch(e) { console.error("Could not load gateways", e); }'''

p_content = p_content.replace(old_load, new_load)
pos_path.write_text(p_content, encoding="utf-8")
print("✅ Fixed POS dropdown to load available gateways")

# ============================================================
# 4. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "sales"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server and try the POS again.")