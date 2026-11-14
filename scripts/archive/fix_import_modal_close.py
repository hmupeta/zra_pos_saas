import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"

content = html_path.read_text(encoding="utf-8")

# 1. Add @click.self to the backdrop so clicking outside closes it
old_backdrop = '''    <!-- Import CSV Modal -->
    <template x-if="showImportModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">'''
new_backdrop = '''    <!-- Import CSV Modal -->
    <template x-if="showImportModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4" @click.self="showImportModal = false">'''
content = content.replace(old_backdrop, new_backdrop)

# 2. Ensure the close 'X' button is present and styled (in case the icon failed to load)
old_header = '''          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">Bulk Import Products</h2>
            <button @click="showImportModal = false" class="text-gray-400 hover:text-gray-600"><i data-lucide="x" class="w-5 h-5"></i></button>
          </div>'''
new_header = '''          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">Bulk Import Products</h2>
            <button @click="showImportModal = false" class="text-gray-500 hover:text-red-500 font-bold text-xl px-2">
              &times;
            </button>
          </div>'''
if old_header in content:
    content = content.replace(old_header, new_header)
else:
    # If the header wasn't matched exactly, just ensure there's an 'X' text fallback
    content = content.replace('<i data-lucide="x" class="w-5 h-5"></i>', '<span class="text-xl">&times;</span>')

# 3. Add a "Cancel" button next to the "Upload & Import" button
old_buttons = '''            <button type="submit" class="btn-primary w-full" :disabled="!csvFile || uploading">
              <span x-show="!uploading">Upload & Import</span>
              <span x-show="uploading">Processing...</span>
            </button>
          </form>'''
new_buttons = '''            <div class="flex gap-2 pt-2">
              <button type="button" @click="showImportModal = false; csvFile = null; importResult = null;" class="btn-secondary flex-1">
                Cancel
              </button>
              <button type="submit" class="btn-primary flex-1" :disabled="!csvFile || uploading">
                <span x-show="!uploading">Upload & Import</span>
                <span x-show="uploading">Processing...</span>
              </button>
            </div>
          </form>'''

content = content.replace(old_buttons, new_buttons)
html_path.write_text(content, encoding="utf-8")

print("✅ Added Cancel button and backdrop click-to-close.")
print("🎉 Done! Restart the server and do a hard refresh (Ctrl + Shift + R).")