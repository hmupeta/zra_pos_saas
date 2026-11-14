import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"

content = html_path.read_text(encoding="utf-8")

# 1. Inject the Button next to "Export CSV"
# Looking at your screenshot, the button says "Export CSV"
old_header = '''      <div class="flex gap-2">
        <a href="/api/auth/export/products/" class="btn-secondary">Export CSV</a>
        <button @click="openReceiveModal(null)" class="btn-secondary">+ Receive Stock</button>
        <button @click="showModal = true" class="btn-primary">+ New Product</button>
      </div>'''

new_header = '''      <div class="flex gap-2">
        <button @click="showImportModal = true" class="btn-secondary bg-green-50 text-green-700 border-green-200 hover:bg-green-100">
          <i data-lucide="upload" class="w-4 h-4 inline mr-1"></i> Import CSV
        </button>
        <a href="/api/auth/export/products/" class="btn-secondary">Export CSV</a>
        <button @click="openReceiveModal(null)" class="btn-secondary">+ Receive Stock</button>
        <button @click="showModal = true" class="btn-primary">+ New Product</button>
      </div>'''

if "Import CSV" not in content:
    if old_header in content:
        content = content.replace(old_header, new_header)
        print("✅ Restored the 'Import CSV' button.")
    else:
        # Fallback: just inject before Export CSV
        content = content.replace(
            '<a href="/api/auth/export/products/" class="btn-secondary">Export CSV</a>',
            '''<button @click="showImportModal = true" class="btn-secondary bg-green-50 text-green-700 border-green-200 hover:bg-green-100 mr-2"><i data-lucide="upload" class="w-4 h-4 inline mr-1"></i> Import CSV</button>
            <a href="/api/auth/export/products/" class="btn-secondary">Export CSV</a>'''
        )
        print("✅ Restored the 'Import CSV' button (fallback method).")

# 2. Inject the Modal before the closing div
import_modal = '''
    <!-- Import CSV Modal -->
    <template x-if="showImportModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">Bulk Import Products</h2>
            <button @click="showImportModal = false" class="text-gray-400 hover:text-gray-600"><i data-lucide="x" class="w-5 h-5"></i></button>
          </div>
          
          <div class="bg-blue-50 text-blue-800 text-sm p-4 rounded-lg mb-4">
            <p class="mb-2"><strong>Instructions:</strong></p>
            <ol class="list-decimal ml-4 space-y-1">
              <li>Download the template below.</li>
              <li>Fill in your products (do not change the column headers).</li>
              <li>Upload the saved CSV file.</li>
            </ol>
            <a href="/api/inventory/products/template/" class="inline-block mt-3 text-blue-600 font-bold hover:underline">
              ⬇️ Download CSV Template
            </a>
          </div>

          <form @submit.prevent="uploadCsv()" class="space-y-4">
            <div class="border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:bg-gray-50 transition relative">
              <input type="file" accept=".csv" @change="handleCsvUpload" class="absolute inset-0 w-full h-full opacity-0 cursor-pointer">
              <i data-lucide="file-spreadsheet" class="w-8 h-8 text-gray-400 mx-auto mb-2"></i>
              <p class="text-sm font-medium text-gray-700" x-text="csvFile ? csvFile.name : 'Click or drag CSV file here'"></p>
              <p class="text-xs text-gray-500 mt-1" x-show="!csvFile">Only .csv files are allowed</p>
            </div>

            <button type="submit" class="btn-primary w-full" :disabled="!csvFile || uploading">
              <span x-show="!uploading">Upload & Import</span>
              <span x-show="uploading">Processing...</span>
            </button>
          </form>
          
          <!-- Upload Results -->
          <div x-show="importResult" class="mt-4 p-4 rounded-lg" :class="importResult?.errors?.length > 0 ? 'bg-yellow-50' : 'bg-green-50'">
            <p class="font-bold text-sm mb-2" x-text="'Import Complete: ' + importResult?.created + ' new products added.'"></p>
            <template x-if="importResult?.errors?.length > 0">
              <div>
                <p class="text-xs text-red-600 font-bold mb-1">Some rows were skipped:</p>
                <ul class="text-xs text-red-600 list-disc ml-4 max-h-24 overflow-y-auto">
                  <template x-for="err in importResult.errors">
                    <li x-text="err"></li>
                  </template>
                </ul>
              </div>
            </template>
          </div>

        </div>
      </div>
    </template>
'''

if "Import CSV Modal" not in content:
    content = content.replace("  </div>\n</div>\n<script>", import_modal + "\n  </div>\n</div>\n<script>")
    print("✅ Restored the Import Modal HTML.")

# 3. Ensure JS variables and functions exist
if "showImportModal: false" not in content:
    content = content.replace(
        "showModal: false, receiveModal: false, saving: false,",
        "showModal: false, receiveModal: false, showImportModal: false, saving: false,\n    csvFile: null, uploading: false, importResult: null,"
    )
    print("✅ Restored Import JS state.")

if "handleCsvUpload(e)" not in content:
    js_upload = '''
    handleCsvUpload(e) {
      if (e.target.files.length > 0) {
        this.csvFile = e.target.files[0];
        this.importResult = null;
      }
    },

    async uploadCsv() {
      if (!this.csvFile) return;
      this.uploading = true;
      this.importResult = null;
      
      try {
        const fd = new FormData();
        fd.append('file', this.csvFile);
        
        const res = await apiFetch('/inventory/products/import/', { method: 'POST', body: fd });
        this.importResult = res;
        this.csvFile = null;
        this.load(); // Reload the product list
      } catch(e) {
        alert(e.response?.data?.error || e.message);
      } finally {
        this.uploading = false;
      }
    },
'''
    content = content.replace("    async create() {", js_upload + "\n    async create() {")
    print("✅ Restored Import JS functions.")

html_path.write_text(content, encoding="utf-8")
print("\n🎉 Done! Restart the server and do a hard refresh (Ctrl + Shift + R).")