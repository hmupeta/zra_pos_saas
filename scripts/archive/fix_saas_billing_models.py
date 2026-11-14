import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Append missing models to saas/models.py
# ============================================================
models_path = BACKEND_PATH / "saas" / "models.py"
content = models_path.read_text(encoding="utf-8")

if "class TenantInvoice" not in content:
    content += '''

class TenantInvoice(models.Model):
    """Invoices sent by the SaaS platform to a tenant."""
    STATUS = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent"),
        ("PAID", "Paid"),
        ("OVERDUE", "Overdue"),
        ("VOID", "Void"),
    ]

    tenant = models.ForeignKey("core.Tenant", on_delete=models.PROTECT, related_name="platform_invoices")
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-invoice_date"]

    def __str__(self):
        return f"{self.invoice_number} · {self.tenant.name}"

class TenantPayment(models.Model):
    """Payments received from tenants."""
    METHODS = [
        ("BANK", "Bank Transfer"),
        ("CASH", "Cash"),
        ("CARD", "Card"),
        ("MOMO", "Mobile Money"),
    ]

    tenant = models.ForeignKey("core.Tenant", on_delete=models.PROTECT, related_name="platform_payments")
    invoice = models.ForeignKey(TenantInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    payment_number = models.CharField(max_length=50, unique=True)
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHODS)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.payment_number} · {self.tenant.name} · K{self.amount}"
'''
    models_path.write_text(content, encoding="utf-8")
print("✅ Added TenantInvoice and TenantPayment to saas/models.py")

# ============================================================
# 2. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "saas"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Fix applied! Restart your server.")