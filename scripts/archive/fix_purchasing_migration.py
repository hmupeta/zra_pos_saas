import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# 1. Delete the broken migration
migrations_dir = BACKEND_PATH / "purchasing" / "migrations"
for f in migrations_dir.glob("0002_*.py"):
    f.unlink()
    print(f"✅ Deleted broken migration: {f.name}")

# 2. Overwrite models.py with safe defaults
models_path = BACKEND_PATH / "purchasing" / "models.py"
new_models = '''
from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

class Supplier(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    tpin = models.CharField(max_length=20, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("tenant", "code")]

    def __str__(self):
        return self.name

    def current_balance(self):
        from django.db.models import Sum
        invs = self.invoices.aggregate(t=Sum('total'))['t'] or 0
        pays = self.payments.aggregate(t=Sum('amount'))['t'] or 0
        return self.opening_balance + invs - pays

class PurchaseOrder(models.Model):
    STATUS = [("DRAFT", "Draft"), ("RECEIVED", "Received"), ("CANCELLED", "Cancelled")]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    po_number = models.CharField(max_length=50, unique=True)
    order_date = models.DateField(default=timezone.now)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.po_number

class SupplierInvoice(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="invoices")
    invoice_number = models.CharField(max_length=50)
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default="UNPAID")

    class Meta:
        unique_together = [("tenant", "invoice_number")]

class SupplierPayment(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="payments")
    invoice = models.ForeignKey(SupplierInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=50, default="BANK")
    reference = models.CharField(max_length=100, blank=True)
'''
models_path.write_text(new_models.strip(), encoding="utf-8")
print("✅ Rebuilt purchasing/models.py with safe defaults")

# 3. Run migrations
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "purchasing"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Fix applied! Run 'python manage.py runserver'")