import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# 1. Fix the printReceipt function to not break HTML parsing
# We split the `</script>` tag into `</scr` + `ipt>`
old_print = """    printReceipt(text) {
      const win = window.open('', '_blank', 'width=400,height=650');
      if (!win) { alert('Allow popups to print receipts'); return; }
      win.document.write(`<html><head><title>Receipt</title><style>body{font-family:'Courier New',monospace;font-size:12px;margin:8px;}pre{white-space:pre-wrap;margin:0;}@media print{body{margin:0;}}</style></head><body><pre>${text}</pre><script>window.onload=()=>{window.print();setTimeout(()=>window.close(),100);}</script></body></html>`);
      win.document.close();
    },"""

new_print = """    printReceipt(text) {
      const win = window.open('', '_blank', 'width=400,height=650');
      if (!win) { alert('Allow popups to print receipts'); return; }
      
      // We safely split the closing script tag so it doesn't break this parent script block
      const closeScript = '</scr' + 'ipt>';
      const html = `<html><head><title>Receipt</title><style>body{font-family:'Courier New',monospace;font-size:12px;margin:8px;}pre{white-space:pre-wrap;margin:0;}@media print{body{margin:0;}}</style></head><body><pre>${text}</pre><script>window.onload=()=>{window.print();setTimeout(()=>window.close(),100);}${closeScript}</body></html>`;
      
      win.document.write(html);
      win.document.close();
    },"""

if old_print in content:
    content = content.replace(old_print, new_print)
    print("✅ Fixed the printReceipt function to prevent HTML parsing crashes.")
else:
    print("⚠️ Could not find the old printReceipt block. Attempting regex fallback.")
    pattern = r"    printReceipt\(text\) \{.*?win\.document\.close\(\);\s*\},"
    content = re.sub(pattern, new_print, content, flags=re.DOTALL)
    print("✅ Fixed printReceipt using regex.")

pos_path.write_text(content, encoding="utf-8")
print("\n🎉 Done! Restart the server and do a HARD REFRESH (Ctrl + Shift + R).")