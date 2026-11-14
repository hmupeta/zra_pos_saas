import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "reports.html"

content = html_path.read_text(encoding="utf-8")

# Find the line that constructs the URL and add 'zra' to the list of tabs that get params
old_line = "const url = (this.tab === 'cash_flow' || this.tab === 'category') ? endpoint + params : endpoint;"
new_line = "const url = (this.tab === 'cash_flow' || this.tab === 'category' || this.tab === 'zra') ? endpoint + params : endpoint;"

if old_line in content:
    content = content.replace(old_line, new_line)
    html_path.write_text(content, encoding="utf-8")
    print("✅ Fixed frontend to send date parameters for the ZRA report.")
else:
    print("⚠️ Could not find the exact URL construction line. It might have been modified.")
    # Fallback: search for the line where it defines the url
    if "this.tab === 'cash_flow'" in content:
         print("Check reports.html around the fetchData function.")

print("\n🎉 Done! Restart the server, refresh the page, and click 'Generate' on the ZRA tab.")