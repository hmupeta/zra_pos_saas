import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# Find the current Open Shift modal block
old_modal = '''  <!-- Open Shift Modal -->
  <div x-show="openShiftModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-xl max-w-md w-full p-6">
      <h2 class="text-xl font-bold mb-4">Open Shift</h2>
      <label class="block text-sm font-medium mb-1">Opening balance (cash in drawer)</label>
      <input type="number" x-model="openingBalance" class="input-field mb-4" />
      <button @click="openShift()" class="btn-primary w-full">Open Shift</button>
    </div>
  </div>'''

# The new modal with a Close button and click-away behavior
new_modal = '''  <!-- Open Shift Modal -->
  <div x-show="openShiftModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="openShiftModal = false">
    <div class="bg-white rounded-xl max-w-md w-full p-6 relative">
      <button @click="openShiftModal = false" class="absolute top-4 right-4 text-gray-400 hover:text-red-500 font-bold text-2xl px-2">
        &times;
      </button>
      <h2 class="text-xl font-bold mb-4">Open Shift</h2>
      <label class="block text-sm font-medium mb-1">Opening balance (cash in drawer)</label>
      <input type="number" x-model="openingBalance" class="input-field mb-4" />
      <button @click="openShift()" class="btn-primary w-full">Open Shift</button>
      <button @click="openShiftModal = false" class="btn-secondary w-full mt-2">Cancel</button>
    </div>
  </div>'''

if old_modal in content:
    content = content.replace(old_modal, new_modal)
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Added Close button and click-away to Open Shift modal.")
else:
    print("⚠️ Could not find the exact Open Shift modal block. Checking for variations...")
    # Fallback: Search for the specific modal and inject a close button via regex
    pattern = r'(<div x-show="openShiftModal".*?<div class="bg-white.*?>)(.*?)(</div>\s*</div>)'
    
    def replacer(match):
        header = match.group(1)
        inner = match.group(2)
        footer = match.group(3)
        
        # Add close button to header
        header_with_close = header + '<button @click="openShiftModal = false" class="absolute top-4 right-4 text-gray-400 hover:text-red-500 font-bold text-2xl px-2">&times;</button>'
        
        # Add Cancel button to inner
        inner_with_cancel = inner + '<button @click="openShiftModal = false" class="btn-secondary w-full mt-2">Cancel</button>'
        
        return header_with_close + inner_with_cancel + footer

    new_content = re.sub(pattern, replacer, content, flags=re.DOTALL)
    
    # Add click-away to backdrop
    new_content = new_content.replace(
        '<div x-show="openShiftModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">',
        '<div x-show="openShiftModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="openShiftModal = false">'
    )
    
    if new_content != content:
        pos_path.write_text(new_content, encoding="utf-8")
        print("✅ Fixed Open Shift modal using regex fallback.")
    else:
        print("❌ Could not fix the modal automatically. Manual check needed.")

print("\n🎉 Done! Restart the server, refresh the POS page, and you can now escape the Open Shift modal.")