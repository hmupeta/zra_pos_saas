import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "sales" / "views.py"

content = views_path.read_text(encoding="utf-8")

# Check if Decimal is imported
if "from decimal import Decimal" not in content:
    content = "from decimal import Decimal\n" + content
    views_path.write_text(content, encoding="utf-8")
    print("✅ Added missing 'Decimal' import to sales/views.py")
else:
    print("✅ 'Decimal' is already imported.")

print("\n🎉 Done! Restart the server and try clicking Reconcile again.")