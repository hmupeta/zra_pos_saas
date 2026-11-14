import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "sales" / "views.py"

content = views_path.read_text(encoding="utf-8")

# Check if Product is imported
if "from inventory.models import Product" not in content:
    # Add it at the top of the file, right after other imports
    content = "from inventory.models import Product\n" + content
    views_path.write_text(content, encoding="utf-8")
    print("✅ Added 'Product' import to sales/views.py")
else:
    print("✅ 'Product' is already imported.")

print("\n🎉 Done! Restart the server and try creating a quotation again.")