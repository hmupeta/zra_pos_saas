import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "quotations.html"

content = html_path.read_text(encoding="utf-8")

# The broken button with the missing icon
old_button = '''                <button type="button" @click.prevent="showCustomerModal = true" class="btn-secondary px-3" title="Add New Customer">
                  <i data-lucide="plus" class="w-4 h-4"></i>
                </button>'''

# The new button with clear text
new_button = '''                <button type="button" @click.prevent="showCustomerModal = true" class="btn-secondary text-sm whitespace-nowrap" title="Add New Customer">
                  + New
                </button>'''

if old_button in content:
    content = content.replace(old_button, new_button)
    html_path.write_text(content, encoding="utf-8")
    print("✅ Replaced the invisible icon button with a clear '+ New' button.")
else:
    # Fallback if spacing is slightly different
    pattern = r'<button type="button" @click\.prevent="showCustomerModal = true".*?</button>'
    if re.search(pattern, content, flags=re.DOTALL):
        content = re.sub(pattern, new_button, content, flags=re.DOTALL)
        html_path.write_text(content, encoding="utf-8")
        print("✅ Replaced button using regex fallback.")
    else:
        print("⚠️ Could not find the 'New Customer' button. Please check quotations.html manually.")

print("\n🎉 Done! Restart the server, refresh the page, and look next to the customer dropdown.")