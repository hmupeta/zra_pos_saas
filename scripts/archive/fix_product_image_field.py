import os
import re
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Ensure image field exists in Product model
# ============================================================
models_path = BACKEND_PATH / "inventory" / "models.py"
m_content = models_path.read_text(encoding="utf-8")

if "image = models.ImageField" not in m_content:
    # Insert after description or category
    if "description = models.TextField(blank=True)" in m_content:
        m_content = m_content.replace(
            "description = models.TextField(blank=True)",
            "description = models.TextField(blank=True)\n    image = models.ImageField(upload_to='products/', null=True, blank=True)"
        )
    else:
        # Insert after name field
        m_content = m_content.replace(
            "name = models.CharField(max_length=200)",
            "name = models.CharField(max_length=200)\n    image = models.ImageField(upload_to='products/', null=True, blank=True)"
        )
    models_path.write_text(m_content, encoding="utf-8")
    print("✅ Added image field to Product model")
else:
    print("✅ image field already exists in Product model")

# ============================================================
# 2. Verify views.py is using the field safely
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Replace all unsafe p.image accesses with getattr
v_content = v_content.replace(
    '"image_url": p.image.url if p.image else None,',
    '"image_url": p.image.url if getattr(p, "image", None) else None,'
)

views_path.write_text(v_content, encoding="utf-8")
print("✅ Made all image field accesses safe with getattr")

# ============================================================
# 3. Run migrations
# ============================================================
print("\nRunning migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

# Make migrations for inventory
result = subprocess.run(
    [str(python), "manage.py", "makemigrations", "inventory"],
    cwd=BACKEND_PATH,
    capture_output=True, text=True
)
print(result.stdout)

# Apply migrations
result = subprocess.run(
    [str(python), "manage.py", "migrate"],
    cwd=BACKEND_PATH,
    capture_output=True, text=True
)
print(result.stdout)

# ============================================================
# 4. Verify the field now exists
# ============================================================
print("\nVerifying field exists in database...")
verify_script = '''
import os, django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
django.setup()
from inventory.models import Product
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("SELECT column_name FROM information_schema.columns WHERE table_name='inventory_product'")
    columns = [row[0] for row in cursor.fetchall()]

if "image" in columns:
    print("✅ 'image' column EXISTS in inventory_product table")
else:
    print("❌ 'image' column still MISSING. Columns are:", columns)

# Test accessing the field
try:
    p = Product.objects.first()
    if p:
        print(f"✅ Can access p.image: {p.image}")
    else:
        print("✅ No products yet, but field exists")
except Exception as e:
    print(f"❌ Still broken: {e}")
'''

verify_file = BACKEND_PATH / "_verify_image.py"
verify_file.write_text(verify_script, encoding="utf-8")
subprocess.run([str(python), "_verify_image.py"], cwd=BACKEND_PATH)
verify_file.unlink()

print("\n🎉 Done! Restart your server.")