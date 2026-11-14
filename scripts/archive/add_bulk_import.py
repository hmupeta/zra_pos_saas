import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Backend: CSV Import View
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

import_view = '''
import csv
from django.http import HttpResponse
from decimal import Decimal, InvalidOperation

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def download_product_template(request):
    """Generates a blank CSV template for importing products."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="product_import_template.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Barcode', 'Product Name', 'Category', 'Cost Price', 'Selling Price', 'Opening Stock', 'Tax Rate'])
    writer.writerow(['8901234567890', 'Coca-Cola 500ml', 'Beverages', '5.60', '8.00', '100', '16'])
    writer.writerow(['8901234567891', 'Bread Loaf', 'Food', '11.00', '15.00', '50', '16'])
    return response

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def import_products_csv(request):
    """Parses an uploaded CSV and creates products."""
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    csv_file = request.FILES.get("file")
    if not csv_file:
        return Response({"error": "No file uploaded"}, status=400)

    if not csv_file.name.endswith('.csv'):
        return Response({"error": "File must be a CSV"}, status=400)

    try:
        decoded_file = csv_file.read().decode('utf-8-sig').splitlines()
        reader = csv.DictReader(decoded_file)
        
        created_count = 0
        errors = []

        # Get default Tax Rate (e.g., 16%) as fallback
        default_tax = TaxRate.objects.filter(tenant=request.tenant, rate=16).first()

        for row_num, row in enumerate(reader, start=2):
            try:
                barcode = row.get('Barcode', '').strip()
                name = row.get('Product Name', '').strip()
                category_name = row.get('Category', 'Uncategorized').strip()
                cost = Decimal(row.get('Cost Price', '0').strip() or '0')
                price = Decimal(row.get('Selling Price', '0').strip() or '0')
                stock = Decimal(row.get('Opening Stock', '0').strip() or '0')
                tax_rate_val = row.get('Tax Rate', '').strip()

                if not barcode or not name:
                    errors.append(f"Row {row_num}: Missing Barcode or Name")
                    continue

                # 1. Handle Category
                category, _ = Category.objects.get_or_create(
                    tenant=request.tenant, name=category_name,
                    defaults={"zra_item_code": "5059690800"}
                )

                # 2. Handle Tax Rate
                tax_rate = default_tax
                if tax_rate_val:
                    try:
                        tax_rate = TaxRate.objects.filter(tenant=request.tenant, rate=Decimal(tax_rate_val)).first() or default_tax
                    except InvalidOperation:
                        pass
                
                if not tax_rate:
                    errors.append(f"Row {row_num}: No valid Tax Rate found.")
                    continue

                # 3. Create Product
                _, created = Product.objects.update_or_create(
                    tenant=request.tenant, company=request.branch, barcode=barcode,
                    defaults={
                        "name": name,
                        "category": category,
                        "tax_rate": tax_rate,
                        "unit_cost": cost,
                        "selling_price": price,
                        "current_stock": stock,
                        "zra_item_code": category.zra_item_code,
                        "is_active": True
                    }
                )
                if created:
                    created_count += 1

            except Exception as e:
                errors.append(f"Row {row_num}: {str(e)}")

        return Response({
            "success": True, 
            "created": created_count, 
            "errors": errors[:10] # Return first 10 errors to avoid huge payloads
        })

    except Exception as e:
        return Response({"error": f"Failed to read file: {str(e)}"}, status=400)
'''

if "def import_products_csv" not in v_content:
    views_path.write_text(v_content + "\n\n" + import_view, encoding="utf-8")

# Update URLs
urls_path = BACKEND_PATH / "inventory" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "import_products_csv" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path("products/template/", views.download_product_template, name="download_product_template"),
    path("products/import/", views.import_products_csv, name="import_products_csv"),'''
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Added CSV Import API endpoints")

# ============================================================
# 2. Frontend: Update Products UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"
h_content = html_path.read_text(encoding="utf-8")

# Add "Import" button next to "+ New Product"
old_buttons = '''      <div class="flex gap-2">
        <button @click="openReceiveModal(null)" class="btn-secondary">+ Receive Stock</button>
        <button @click="showModal = true" class="btn-primary">+ New Product</button>
      </div>'''

new_buttons = '''      <div class="flex gap-2">
        <button @click="showImportModal = true" class="btn-secondary bg-green-50 text-green-700 border-green-200 hover:bg-green-100">
          <i data-lucide="upload" class="w-4 h-4 inline mr-1"></i> Import CSV
        </button>
        <button @click="openReceiveModal(null)" class="btn-secondary">+ Receive Stock</button>
        <button @click="showModal = true" class="btn-primary">+ New Product</button>
      </div>'''
h_content = h_content.replace(old_buttons, new_buttons)

# Add the Import Modal before the closing div
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
h_content = h_content.replace("  </div>\n</div>\n<script>", import_modal + "\n  </div>\n</div>\n<script>")

# Update JS state
h_content = h_content.replace(
    "showModal: false, receiveModal: false, saving: false,",
    "showModal: false, receiveModal: false, showImportModal: false, saving: false,\n    csvFile: null, uploading: false, importResult: null,"
)

# Add JS functions for upload
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
h_content = h_content.replace("    async create() {", js_upload + "\n    async create() {")

html_path.write_text(h_content, encoding="utf-8")
print("✅ Updated Products UI with Bulk CSV Import")

print("\n🎉 Done! Restart the server.")