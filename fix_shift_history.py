import os
import re
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add missing fields to Shift model
# ============================================================
models_path = BACKEND_PATH / "sales" / "models.py"
m_content = models_path.read_text(encoding="utf-8")

if "expected_amount =" not in m_content:
    m_content = m_content.replace(
        "opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)",
        "opening_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0)\n    closing_balance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)\n    expected_amount = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)\n    actual_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)\n    variance = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)"
    )
    models_path.write_text(m_content, encoding="utf-8")
    print("✅ Added missing fields to Shift model.")
else:
    print("✅ Shift model already has the required fields.")

# ============================================================
# 2. Update shift views to handle these fields safely
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Ensure shifts_list uses getattr or calculates values safely
old_list = '''        "expected_cash": float(s.expected_amount or 0),'''
new_list = '''        "expected_cash": float(getattr(s, 'expected_amount', 0) or 0),'''
v_content = v_content.replace(old_list, new_list)

# Ensure shift_details handles them safely too
old_details = '''            "expected_cash": float(shift.expected_amount or 0),'''
new_details = '''            "expected_cash": float(getattr(shift, 'expected_amount', 0) or 0),'''
v_content = v_content.replace(old_details, new_details)

views_path.write_text(v_content, encoding="utf-8")
print("✅ Updated views to safely handle shift fields.")

# ============================================================
# 3. Run Migrations
# ============================================================
print("\nRunning migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "sales"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server and go to Shift History.")