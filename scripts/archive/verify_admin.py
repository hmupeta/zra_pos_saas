import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def main():
    print("Verifying Admin APIs...")
    test_script = """
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from rest_framework.test import APIClient
from core.models import User

try:
    admin = User.objects.get(username='admin')
except User.DoesNotExist:
    print("❌ Admin user not found! Run fix_seed.py")
    exit()

client = APIClient()
client.force_authenticate(user=admin)

print("- Testing /api/saas/admin/dashboard/ ...")
# FIX: We pass HTTP_HOST='localhost' so Django doesn't block the testserver
res = client.get('/api/saas/admin/dashboard/', HTTP_HOST='localhost')
if res.status_code == 200:
    print("  ✅ Dashboard API is working perfectly.")
else:
    print(f"  ❌ Dashboard API FAILED with {res.status_code}")
    print(f"     Response: {res.content.decode()[:200]}")

print("- Testing /api/saas/admin/tenants/ ...")
res = client.get('/api/saas/admin/tenants/', HTTP_HOST='localhost')
if res.status_code == 200:
    print(f"  ✅ Tenants API is working. Found {len(res.json())} tenants.")
else:
    print(f"  ❌ Tenants API FAILED with {res.status_code}")
    print(f"     Response: {res.content.decode()[:200]}")
"""
    test_file = BACKEND_PATH / "_test_admin.py"
    test_file.write_text(test_script, encoding="utf-8")
    
    venv = BACKEND_PATH / "venv"
    python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
    subprocess.run([str(python), "_test_admin.py"], cwd=BACKEND_PATH)
    test_file.unlink()

if __name__ == "__main__":
    main()