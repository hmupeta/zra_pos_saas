import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# 1. Completely overwrite the Customer model
models_path = BACKEND_PATH / "customers" / "models.py"
new_model = '''
from django.db import models

class Customer(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE, null=True, blank=True)
    customer_id = models.CharField(max_length=20)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100, blank=True)
    business_name = models.CharField(max_length=200, blank=True)
    phone_number = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    loyalty_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    kyc_status = models.CharField(max_length=20, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("tenant", "customer_id")]

    @property
    def full_name(self):
        if self.business_name:
            return self.business_name
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.phone_number

    def __str__(self):
        return self.full_name
'''
models_path.write_text(new_model.strip(), encoding="utf-8")
print("✅ Rebuilt customers/models.py with full_name property")

# 2. Run Migrations
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "customers"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Fix applied! Restart your server.")