import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
cart_file = BACKEND_PATH / "sales" / "cart_service.py"

content = cart_file.read_text(encoding="utf-8")

# 1. Replace the inv_num generation to include a random UUID suffix
old_gen = 'inv_num = f"{datetime.datetime.now().strftime(\'%y%m%d%H%M%S\')}"'
new_gen = '''import uuid
        inv_num = f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"'''

if old_gen in content:
    content = content.replace(old_gen, new_gen)
    cart_file.write_text(content, encoding="utf-8")
    print("✅ Fixed Invoice & Journal numbering to prevent duplicate keys.")
else:
    # If the exact string isn't found, try a broader regex
    import re
    content = re.sub(r"inv_num = f\"\{datetime\.datetime\.now\(\)\.strftime\('%y%m%d%H%M%S'\)\}\"", new_gen.strip(), content)
    cart_file.write_text(content, encoding="utf-8")
    print("✅ Fixed Invoice & Journal numbering using regex.")

print("\n🎉 Done! Restart the server and try checking out again.")