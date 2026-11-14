import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "sales" / "views.py"

content = views_path.read_text(encoding="utf-8")

# Check if StockReservation is imported
if "StockReservation" not in content.split("def ")[0]:  # Check only the import section
    # Add the import at the top or append to existing model imports
    if "from .models import " in content:
        # Append to existing import
        content = content.replace(
            "from .models import ",
            "from .models import StockReservation, StockReservationItem, "
        )
    else:
        # Add a new import line at the very top
        content = "from .models import StockReservation, StockReservationItem\n" + content
    
    views_path.write_text(content, encoding="utf-8")
    print("✅ Added StockReservation imports to sales/views.py")
else:
    print("✅ Imports already exist.")

print("\n🎉 Done! Restart the server and refresh the Reservations page.")