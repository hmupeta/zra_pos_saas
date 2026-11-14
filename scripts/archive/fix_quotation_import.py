import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "sales" / "views.py"

content = views_path.read_text(encoding="utf-8")

# Check if Quotation is imported
if "Quotation" not in content.split("def ")[0]:  # Only check the import section
    if "from .models import" in content:
        # Find the exact line and append
        # The line probably looks like: from .models import Shift, Invoice, InvoiceItem, StockReservation, StockReservationItem
        import re
        match = re.search(r"from \.models import (.+)", content)
        if match:
            current_imports = match.group(1).strip()
            if "Quotation" not in current_imports:
                new_imports = current_imports + ", Quotation, QuotationItem"
                content = content.replace(
                    f"from .models import {current_imports}",
                    f"from .models import {new_imports}",
                    1
                )
    else:
        content = "from .models import Quotation, QuotationItem\n" + content
    
    views_path.write_text(content, encoding="utf-8")
    print("✅ Added Quotation and QuotationItem imports to sales/views.py")
else:
    print("✅ Quotation already imported.")

# Also verify Decimal is imported (used by quotation views)
if "from decimal import Decimal" not in content:
    content = "from decimal import Decimal\n" + content
    views_path.write_text(content, encoding="utf-8")
    print("✅ Ensured 'Decimal' is imported.")

print("\n🎉 Done! Restart the server and refresh the Quotations page.")