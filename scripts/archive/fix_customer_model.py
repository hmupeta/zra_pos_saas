import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Fix the Customer Model
# ============================================================
models_path = BACKEND_PATH / "customers" / "models.py"
content = models_path.read_text(encoding="utf-8")

# Ensure total_spent exists
if "total_spent = models.DecimalField" not in content:
    content = content.replace(
        "loyalty_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)",
        "loyalty_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)\n    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)"
    )

# Add full_name property
if "def full_name" not in content:
    # Insert the property right before the __str__ method
    content = content.replace(
        "    def __str__(self):",
        """    @property
    def full_name(self):
        if self.business_name:
            return self.business_name
        name = f"{self.first_name} {self.last_name}".strip()
        return name if name else self.phone_number

    def __str__(self):"""
    )
    
models_path.write_text(content, encoding="utf-8")
print("✅ Updated customers/models.py with full_name property")

# ============================================================
# 2. Run Migrations to apply any missed changes
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "customers"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Fix applied! Restart your server with: python manage.py runserver")