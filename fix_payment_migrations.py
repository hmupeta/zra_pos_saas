import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Ensure fields exist in the model
# ============================================================
models_path = BACKEND_PATH / "payments" / "models.py"
content = models_path.read_text(encoding="utf-8")

if "mtn_subscription_key" not in content:
    content = content.replace(
        "extra_config = models.JSONField(default=dict, blank=True)",
        "extra_config = models.JSONField(default=dict, blank=True)\n    mtn_subscription_key = models.CharField(max_length=200, blank=True)\n    mtn_api_user = models.CharField(max_length=200, blank=True)\n    mtn_api_key = models.CharField(max_length=200, blank=True)\n    mtn_target_env = models.CharField(max_length=50, default='sandbox')"
    )
    models_path.write_text(content, encoding="utf-8")
    print("✅ Re-applied MTN fields to payments/models.py")

# ============================================================
# 2. Force Migrations
# ============================================================
print("Running makemigrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "payments"], cwd=BACKEND_PATH)

print("Running migrate...")
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Fix applied! Restart your server.")