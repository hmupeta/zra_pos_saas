import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Models to use EncryptedCharField
# ============================================================
models_path = BACKEND_PATH / "payments" / "models.py"
content = models_path.read_text(encoding="utf-8")

# Add the import if it doesn't exist
if "from core.encryption import EncryptedCharField" not in content:
    content = "from core.encryption import EncryptedCharField\n" + content

# Replace standard CharFields with EncryptedCharField for sensitive fields
content = content.replace(
    "merchant_id = models.CharField(max_length=200, blank=True)",
    "merchant_id = EncryptedCharField(blank=True)"
).replace(
    "api_key = models.CharField(max_length=200, blank=True)",
    "api_key = EncryptedCharField(blank=True)"
).replace(
    "api_secret = models.CharField(max_length=200, blank=True)",
    "api_secret = EncryptedCharField(blank=True)"
).replace(
    "mtn_subscription_key = models.CharField(max_length=200, blank=True)",
    "mtn_subscription_key = EncryptedCharField(blank=True)"
).replace(
    "mtn_api_user = models.CharField(max_length=200, blank=True)",
    "mtn_api_user = EncryptedCharField(blank=True)"
).replace(
    "mtn_api_key = models.CharField(max_length=200, blank=True)",
    "mtn_api_key = EncryptedCharField(blank=True)"
)

models_path.write_text(content, encoding="utf-8")
print("✅ Updated payment models to use EncryptedCharField")

# ============================================================
# 2. Fix the Test Connection View
# ============================================================
views_path = BACKEND_PATH / "payments" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Fix the broken resolve_for_branch call
v_content = v_content.replace(
    "config = BranchPaymentConfig.resolve_for_branch(request.branch, provider)",
    "config = BranchPaymentConfig.objects.filter(branch=request.branch, provider=provider).first()"
)

views_path.write_text(v_content, encoding="utf-8")
print("✅ Fixed test_gateway_connection view")

# ============================================================
# 3. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "payments"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server and try testing the connection again.")