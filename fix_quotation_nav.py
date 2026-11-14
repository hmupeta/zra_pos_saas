import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"

content = nav_path.read_text(encoding="utf-8")

# 1. Check if it's already there
if 'href="/quotations"' in content:
    print("✅ Quotations link already exists in the sidebar.")
else:
    # 2. Use a regex to find the Invoices link and insert Quotations right after it
    # This matches the <a> tag for Invoices regardless of its exact inner HTML
    pattern = r'(<a href="/invoices"[^>]*>.*?</a>)'
    
    if re.search(pattern, content, flags=re.DOTALL):
        # Insert the Quotations link after Invoices
        new_link = r'\1\n    <a href="/quotations" class="nav-link"><i data-lucide="file-signature" class="w-4 h-4 mr-3"></i> Quotations</a>'
        content = re.sub(pattern, new_link, content, count=1, flags=re.DOTALL)
        nav_path.write_text(content, encoding="utf-8")
        print("✅ Successfully added Quotations to the sidebar.")
    else:
        # Fallback: insert before Customers
        pattern_customers = r'(<a href="/customers"[^>]*>)'
        if re.search(pattern_customers, content):
            new_link = r'<a href="/quotations" class="nav-link"><i data-lucide="file-signature" class="w-4 h-4 mr-3"></i> Quotations</a>\n    \1'
            content = re.sub(pattern_customers, new_link, content, count=1)
            nav_path.write_text(content, encoding="utf-8")
            print("✅ Added Quotations to the sidebar (fallback method).")
        else:
            print("❌ Could not find Invoices or Customers link to insert next to.")

print("\n🎉 Done! Restart the server and do a HARD REFRESH (Ctrl + Shift + R).")