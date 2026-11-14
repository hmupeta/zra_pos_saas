import os
import re
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Ensure Backend Route & View exist
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
w_content = views_web.read_text(encoding="utf-8")
if "def reservations_page" not in w_content:
    w_content += "\n\ndef reservations_page(request):\n    return render(request, 'pos/reservations.html')\n"
    views_web.write_text(w_content, encoding="utf-8")
    print("✅ Added reservations_page view.")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
wu_content = urls_web.read_text(encoding="utf-8")
if "/reservations" not in wu_content:
    wu_content = wu_content.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('reservations', views_web.reservations_page, name='reservations_page'),"
    )
    urls_web.write_text(wu_content, encoding="utf-8")
    print("✅ Added /reservations URL route.")

# ============================================================
# 2. Force Inject "Reservations" into the Sidebar
# ============================================================
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
n_content = nav_path.read_text(encoding="utf-8")

if 'href="/reservations"' in n_content:
    print("✅ Reservations link already exists in sidebar.")
else:
    # Find the Quotations link and add Reservations right after it
    pattern = r'(<a href="/quotations"[^>]*>.*?</a>)'
    
    if re.search(pattern, n_content, flags=re.DOTALL):
        # Insert the new link after Quotations
        new_link = r'\1\n    <a href="/reservations" class="nav-link"><i data-lucide="lock" class="w-4 h-4 mr-3"></i> Reservations</a>'
        n_content = re.sub(pattern, new_link, n_content, count=1, flags=re.DOTALL)
        nav_path.write_text(n_content, encoding="utf-8")
        print("✅ Successfully injected Reservations into the sidebar (after Quotations).")
    else:
        # Fallback: Insert after Invoices if Quotations link isn't found
        pattern_inv = r'(<a href="/invoices"[^>]*>.*?</a>)'
        if re.search(pattern_inv, n_content, flags=re.DOTALL):
            new_link = r'\1\n    <a href="/reservations" class="nav-link"><i data-lucide="lock" class="w-4 h-4 mr-3"></i> Reservations</a>'
            n_content = re.sub(pattern_inv, new_link, n_content, count=1, flags=re.DOTALL)
            nav_path.write_text(n_content, encoding="utf-8")
            print("✅ Successfully injected Reservations into the sidebar (after Invoices).")
        else:
            print("❌ Could not find Invoices or Quotations link to insert next to.")

# ============================================================
# 3. Verify Template Exists (Create if missing)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "reservations.html"
if not html_path.exists():
    print("⚠️ reservations.html is missing. Re-creating a basic version...")
    # (If the previous script failed entirely, we need the file. 
    # For brevity, I'm creating a minimal working version here. 
    # If the full UI was created earlier, this won't overwrite it.)
    basic_html = '''
{% extends "pos/base.html" %}
{% block title %}Reservations{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 p-6">
    <h1 class="text-2xl font-bold">Reservations</h1>
    <p class="text-gray-500">Please run the full reservation setup script if this page is blank.</p>
  </div>
</div>
{% endblock %}
'''
    html_path.write_text(basic_html.strip(), encoding="utf-8")
else:
    print("✅ reservations.html already exists.")

# ============================================================
# 4. Run Migrations (Just in case)
# ============================================================
print("\nRunning migrations to ensure database is up to date...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server and do a HARD REFRESH (Ctrl + Shift + R).")