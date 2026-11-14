import os
import subprocess
import platform
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def get_python():
    venv = BACKEND_PATH / "venv"
    if platform.system() == "Windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"

def main():
    python = get_python()
    
    print("1. Ensuring database is fully migrated...")
    subprocess.run([str(python), "manage.py", "makemigrations", "saas"], cwd=BACKEND_PATH)
    subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)
    print()
    
    print("2. Testing Admin APIs from the backend...")
    test_script = """
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from rest_framework.test import APIClient
from core.models import User
from saas.permissions import IsPlatformAdmin

try:
    admin = User.objects.get(username='admin')
except User.DoesNotExist:
    print("❌ Admin user not found! Run fix_seed.py")
    exit()

client = APIClient()
client.force_authenticate(user=admin)

print("- Testing /api/saas/admin/dashboard/ ...")
res = client.get('/api/saas/admin/dashboard/')
if res.status_code == 200:
    print("  ✅ Dashboard API is working perfectly.")
else:
    print(f"  ❌ Dashboard API FAILED with {res.status_code}")
    print(f"     Response: {res.content.decode()}")

print("- Testing /api/saas/admin/tenants/ ...")
res = client.get('/api/saas/admin/tenants/')
if res.status_code == 200:
    print(f"  ✅ Tenants API is working. Found {len(res.json())} tenants.")
else:
    print(f"  ❌ Tenants API FAILED with {res.status_code}")
    print(f"     Response: {res.content.decode()}")
"""
    test_file = BACKEND_PATH / "_test_api.py"
    test_file.write_text(test_script, encoding="utf-8")
    subprocess.run([str(python), "_test_api.py"], cwd=BACKEND_PATH)
    test_file.unlink()
    print()

    print("3. Patching frontend to show errors instead of freezing...")
    # Patch Dashboard
    dash_path = BACKEND_PATH / "templates" / "pos" / "admin" / "dashboard.html"
    if dash_path.exists():
        content = dash_path.read_text(encoding="utf-8")
        content = content.replace(
            "async load() {\n      this.data = await apiFetch('/saas/admin/dashboard/');",
            "async load() {\n      try {\n        this.data = await apiFetch('/saas/admin/dashboard/');"
        )
        content = content.replace(
            "      ];\n    }\n  }\n}",
            "      ];\n      } catch (e) {\n        alert('Dashboard Error: ' + e.message);\n      }\n    }\n  }\n}"
        )
        dash_path.write_text(content, encoding="utf-8")
        print("  ✅ Patched dashboard.html error handling")

    # Patch Tenants
    tenants_path = BACKEND_PATH / "templates" / "pos" / "admin" / "tenants.html"
    if tenants_path.exists():
        content = tenants_path.read_text(encoding="utf-8")
        content = content.replace(
            "async load() {\n      const q = new URLSearchParams",
            "async load() {\n      try {\n        const q = new URLSearchParams"
        )
        content = content.replace(
            "this.tenants = await apiFetch(`/saas/admin/tenants/?${q}`);\n    },",
            "this.tenants = await apiFetch(`/saas/admin/tenants/?${q}`);\n      } catch (e) {\n        alert('Tenants Error: ' + e.message);\n      }\n    },"
        )
        tenants_path.write_text(content, encoding="utf-8")
        print("  ✅ Patched tenants.html error handling")

    print("\n🎉 Done! Restart your server.")

if __name__ == "__main__":
    main()