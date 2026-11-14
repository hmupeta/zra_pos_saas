import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Ensure the Customer model has the credit fields
# ============================================================
models_path = BACKEND_PATH / "customers" / "models.py"
m_content = models_path.read_text(encoding="utf-8")

if "credit_limit =" not in m_content:
    m_content = m_content.replace(
        "loyalty_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)",
        "loyalty_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)\n    credit_limit = models.DecimalField(max_digits=12, decimal_places=2, default=0)\n    account_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)"
    )
    models_path.write_text(m_content, encoding="utf-8")
    print("✅ Added credit_limit and account_balance to Customer model.")
else:
    print("✅ Credit fields already exist in Customer model.")

# ============================================================
# 2. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "customers"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

# ============================================================
# 3. Verify the fields exist in the database
# ============================================================
verify_script = '''
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='customers_customer'")
    columns = [row[0] for row in cursor.fetchall()]

if "credit_limit" in columns:
    print("✅ 'credit_limit' column EXISTS in customers_customer table")
else:
    print("❌ 'credit_limit' column MISSING!")

if "account_balance" in columns:
    print("✅ 'account_balance' column EXISTS in customers_customer table")
else:
    print("❌ 'account_balance' column MISSING!")

from customers.models import Customer
try:
    c = Customer.objects.first()
    if c:
        print(f"✅ Can access c.credit_limit: {c.credit_limit}")
    else:
        print("✅ No customers yet, but field exists")
except Exception as e:
    print(f"❌ Still broken: {e}")
'''

verify_file = BACKEND_PATH / "_verify_credit.py"
verify_file.write_text(verify_script, encoding="utf-8")
subprocess.run([str(python), "_verify_credit.py"], cwd=BACKEND_PATH)
verify_file.unlink()

print("\n🎉 Done! Restart the server.")