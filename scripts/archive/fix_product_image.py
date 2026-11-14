import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def get_python():
    venv = BACKEND_PATH / "venv"
    if platform.system() == "Windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"

# ============================================================
# 1. Ensure the model has the image field
# ============================================================
models_path = BACKEND_PATH / "inventory" / "models.py"
content = models_path.read_text(encoding="utf-8")

if "image = models.ImageField" not in content:
    print("Adding image field to models.py...")
    content = content.replace(
        "description = models.TextField(blank=True)",
        "description = models.TextField(blank=True)\n    image = models.ImageField(upload_to='products/', null=True, blank=True)"
    )
    models_path.write_text(content, encoding="utf-8")
else:
    print("✅ Image field already exists in models.py")

# ============================================================
# 2. Add a safety check in views.py
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
views_content = views_path.read_text(encoding="utf-8")

# Replace the specific line that is crashing with a safe getattr check
views_content = views_content.replace(
    '"image_url": p.image.url if p.image else None,',
    '"image_url": p.image.url if getattr(p, "image", None) else None,'
)

views_path.write_text(views_content, encoding="utf-8")
print("✅ Added safety check in views.py")

# ============================================================
# 3. Force Migrations
# ============================================================
python = get_python()
print("\nRunning makemigrations...")
subprocess.run([str(python), "manage.py", "makemigrations", "inventory"], cwd=BACKEND_PATH)

print("\nRunning migrate...")
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Fix applied! Restart your server with: python manage.py runserver")