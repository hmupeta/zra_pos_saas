import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def main():
    print("1. Creating missing saas/permissions.py...")
    perms_path = BACKEND_PATH / "saas" / "permissions.py"
    perms_path.parent.mkdir(parents=True, exist_ok=True)
    
    content = '''
from rest_framework.permissions import BasePermission

class IsPlatformAdmin(BasePermission):
    """Only allows users with user_type = PLATFORM_ADMIN."""
    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and getattr(request.user, "user_type", None) == "PLATFORM_ADMIN"
        )
'''
    perms_path.write_text(content.strip(), encoding="utf-8")
    print("  ✅ Created saas/permissions.py")

    print("\n2. Testing Admin APIs again...")
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
    
    venv = BACKEND_PATH / "venv"
    python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
    subprocess.run([str(python), "_test_api.py"], cwd=BACKEND_PATH)
    test_file.unlink()

if __name__ == "__main__":
    main()