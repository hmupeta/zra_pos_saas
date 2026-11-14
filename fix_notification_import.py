import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "core" / "views.py"

content = views_path.read_text(encoding="utf-8")

# Check if SystemNotification is imported
if "from .models import SystemNotification" not in content:
    # If there's already an import from .models, append to it
    if "from .models import" in content:
        # Simple string replacement (assuming it looks like `from .models import User, Company...`)
        content = content.replace(
            "from .models import",
            "from .models import SystemNotification, ",
            1
        )
    else:
        # Otherwise, add it at the top
        content = "from .models import SystemNotification\n" + content
    
    views_path.write_text(content, encoding="utf-8")
    print("✅ Added SystemNotification import to core/views.py")
else:
    print("✅ SystemNotification already imported.")

print("\n🎉 Done! Restart your server and refresh the page.")