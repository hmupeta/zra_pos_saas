import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def patch_file(path, old, new):
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if old in content:
        content = content.replace(old, new)
        path.write_text(content, encoding="utf-8")
        print(f"✅ Fixed Export button in {path.name}")
    else:
        print(f"⚠️ Could not find Export button in {path.name}")

# 1. Define the JS function to handle the download
js_function = """
    async exportCsv() {
      try {
        const res = await fetch('/api/auth/export/products/', {
          headers: { 'Authorization': `Token ${localStorage.getItem('token')}` }
        });
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'products.csv';
        a.click();
      } catch (e) {
        alert(e.message);
      }
    },
"""

# 2. Fix Products UI
patch_file(
    BACKEND_PATH / "templates" / "pos" / "products.html",
    '<a href="/api/auth/export/products/" class="btn-secondary">Export CSV</a>',
    '<button @click="exportCsv()" class="btn-secondary">Export CSV</button>'
)
patch_file(
    BACKEND_PATH / "templates" / "pos" / "products.html",
    "    async create() {",
    js_function + "\n    async create() {"
)

# 3. Fix Invoices UI
patch_file(
    BACKEND_PATH / "templates" / "pos" / "invoices.html",
    '<a href="/api/auth/export/invoices/" class="btn-secondary text-sm">Export CSV</a>',
    '<button @click="exportCsv()" class="btn-secondary text-sm">Export CSV</button>'
)
patch_file(
    BACKEND_PATH / "templates" / "pos" / "invoices.html",
    "    async load() {",
    """
    async exportCsv() {
      try {
        const res = await fetch('/api/auth/export/invoices/', {
          headers: { 'Authorization': `Token ${localStorage.getItem('token')}` }
        });
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'invoices.csv';
        a.click();
      } catch (e) {
        alert(e.message);
      }
    },

    async load() {"""
)

# 4. Fix Customers UI
patch_file(
    BACKEND_PATH / "templates" / "pos" / "customers.html",
    '<a href="/api/auth/export/customers/" class="btn-secondary text-sm">Export CSV</a>',
    '<button @click="exportCsv()" class="btn-secondary text-sm">Export CSV</button>'
)
patch_file(
    BACKEND_PATH / "templates" / "pos" / "customers.html",
    "    async load() {",
    """
    async exportCsv() {
      try {
        const res = await fetch('/api/auth/export/customers/', {
          headers: { 'Authorization': `Token ${localStorage.getItem('token')}` }
        });
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'customers.csv';
        a.click();
      } catch (e) {
        alert(e.message);
      }
    },

    async load() {"""
)

print("\n🎉 Done! Restart the server, hard refresh (Ctrl + Shift + R), and try exporting again.")