import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "inventory" / "views.py"

content = views_path.read_text(encoding="utf-8")

# Check if the import is missing and add it
if "from rest_framework.decorators import parser_classes" not in content:
    content = "from rest_framework.decorators import parser_classes\n" + content
    views_path.write_text(content, encoding="utf-8")
    print("✅ Added missing 'parser_classes' import to inventory/views.py")
else:
    print("✅ 'parser_classes' import already exists.")

print("\n🎉 Done! Restart the server.")