import os
from pathlib import Path
import re

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Backend (reports/views.py)
# ============================================================
views_path = BACKEND_PATH / "reports" / "views.py"
content = views_path.read_text(encoding="utf-8")

new_endpoints = '''
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def zra_tax_summary(request):
    """Calculates Output VAT for ZRA filings."""
    start = request.query_params.get("start_date")
    end = request.query_params.get("end_date")
    
    if not start or not end:
        return Response({"error": "start_date and end_date required"}, status=400)

    qs = branch_filter(request, Invoice.objects.filter(
        status="PAID", created_at__date__gte=start, created_at__date__lte=end
    ))
    
    agg = qs.aggregate(
        gross_sales=Sum("total"),
        net_sales=Sum("subtotal"),
        output_vat=Sum("tax_total"),
        tx_count=Count("id")
    )

    return Response({
        "period": {"start": start, "end": end},
        "gross_sales": float(agg["gross_sales"] or 0),
        "net_sales": float(agg["net_sales"] or 0),
        "output_vat": float(agg["output_vat"] or 0),
        "transaction_count": agg["tx_count"] or 0,
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def sales_by_category(request):
    """Revenue breakdown by product category."""
    start = request.query_params.get("start_date")
    end = request.query_params.get("end_date")
    
    if not start or not end:
        return Response({"error": "Dates required"}, status=400)

    qs = InvoiceItem.objects.filter(
        invoice__in=branch_filter(request, Invoice.objects.filter(
            status="PAID", created_at__date__gte=start, created_at__date__lte=end
        ))
    ).values('product__category__name').annotate(
        revenue=Sum('total'),
        qty_sold=Sum('quantity')
    ).order_by('-revenue')

    return Response([{
        "category": item["product__category__name"],
        "revenue": float(item["revenue"]),
        "qty": float(item["qty_sold"])
    } for item in qs])
'''

if "def zra_tax_summary" not in content:
    views_path.write_text(content + "\n\n" + new_endpoints, encoding="utf-8")
print("✅ Added ZRA Tax and Category endpoints")

# ============================================================
# 2. Update URLs
# ============================================================
urls_path = BACKEND_PATH / "reports" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")

if "zra_tax_summary" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path("zra-tax/", views.zra_tax_summary, name="zra_tax_summary"),
    path("sales-by-category/", views.sales_by_category, name="sales_by_category"),'''
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Updated reports/urls.py")

# ============================================================
# 3. Update Frontend (reports.html)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "reports.html"
html_content = html_path.read_text(encoding="utf-8")

# Add new tabs to the array
html_content = html_content.replace(
    "tabs: [\n      { id: 'trial', label: 'Trial Balance' },\n      { id: 'balance', label: 'Balance Sheet' },\n      { id: 'income', label: 'Income Statement' },\n    ],",
    "tabs: [\n      { id: 'trial', label: 'Trial Balance' },\n      { id: 'balance', label: 'Balance Sheet' },\n      { id: 'income', label: 'Income Statement' },\n      { id: 'tax', label: 'ZRA Tax Summary' },\n      { id: 'category', label: 'Sales by Category' },\n    ],"
)

# Add Date Range Selector to the UI (Visible only on Tax/Category tabs)
html_content = html_content.replace(
    '<h1 class="text-2xl font-bold">Financial Reports</h1>',
    '''<div>
      <h1 class="text-2xl font-bold">Financial Reports</h1>
      <div x-show="['tax', 'category'].includes(tab)" class="flex gap-2 mt-2">
        <input type="date" x-model="startDate" class="input-field w-40 text-sm">
        <input type="date" x-model="endDate" class="input-field w-40 text-sm">
        <button @click="loadCustom()" class="btn-primary text-sm">Generate</button>
      </div>
    </div>'''
)

# Add the HTML blocks for the new tabs
new_tabs_html = '''
    <!-- ZRA Tax Summary -->
    <div x-show="tab === 'tax' && data" class="card p-6 max-w-2xl">
      <h2 class="font-semibold text-lg mb-4">ZRA VAT Return Summary</h2>
      <div class="grid grid-cols-2 gap-4 border-b pb-4 mb-4">
        <div>
          <div class="text-sm text-gray-500">Gross Sales (VAT Inclusive)</div>
          <div class="text-xl font-bold" x-text="formatCurrency(data?.gross_sales)"></div>
        </div>
        <div>
          <div class="text-sm text-gray-500">Output VAT Collected</div>
          <div class="text-xl font-bold text-brand-700" x-text="formatCurrency(data?.output_vat)"></div>
        </div>
        <div>
          <div class="text-sm text-gray-500">Net Sales (Excluding VAT)</div>
          <div class="text-xl font-semibold" x-text="formatCurrency(data?.net_sales)"></div>
        </div>
        <div>
          <div class="text-sm text-gray-500">Total Transactions</div>
          <div class="text-xl font-semibold" x-text="data?.transaction_count"></div>
        </div>
      </div>
      <div class="bg-blue-50 text-blue-800 text-sm p-3 rounded">
        <strong>Note:</strong> This shows Output VAT. To calculate your final ZRA liability, subtract your Input VAT (from Purchases).
      </div>
      <button @click="downloadCSV('Tax_Summary', data)" class="btn-secondary mt-4 w-full">Export CSV</button>
    </div>

    <!-- Sales by Category -->
    <div x-show="tab === 'category' && data" class="card overflow-hidden">
      <div class="p-4 border-b flex justify-between items-center bg-gray-50">
        <h2 class="font-semibold">Revenue by Category</h2>
        <button @click="downloadCategoryCSV()" class="btn-secondary text-xs">Export CSV</button>
      </div>
      <table class="w-full text-sm">
        <thead class="bg-gray-100 text-left text-xs uppercase">
          <tr><th class="px-4 py-3">Category</th><th class="px-4 py-3 text-right">Qty Sold</th><th class="px-4 py-3 text-right">Total Revenue</th></tr>
        </thead>
        <tbody>
          <template x-for="c in data" :key="c.category">
            <tr class="border-t">
              <td class="px-4 py-3 font-medium" x-text="c.category"></td>
              <td class="px-4 py-3 text-right" x-text="c.qty"></td>
              <td class="px-4 py-3 text-right font-bold" x-text="formatCurrency(c.revenue)"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
'''
html_content = html_content.replace("</div>\n\n<script>", new_tabs_html + "\n  </div>\n\n<script>")

# Update JS to handle dates and new API calls
html_content = html_content.replace(
    "tab: 'trial', data: null, ledgerData: null,",
    "tab: 'trial', data: null, ledgerData: null,\n    startDate: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],\n    endDate: new Date().toISOString().split('T')[0],"
)

new_js_logic = '''
    async loadCustom() {
      if (this.tab === 'tax') {
        this.data = await apiFetch(`/reports/zra-tax/?start_date=${this.startDate}&end_date=${this.endDate}`);
      } else if (this.tab === 'category') {
        this.data = await apiFetch(`/reports/sales-by-category/?start_date=${this.startDate}&end_date=${this.endDate}`);
      }
    },

    downloadCSV(filename, obj) {
      let csv = Object.keys(obj).map(k => `"${k}","${obj[k]}"`).join("\\n");
      this.triggerDownload(csv, filename);
    },

    downloadCategoryCSV() {
      if (!this.data) return;
      let csv = "Category,Qty Sold,Revenue\\n" + this.data.map(c => `"${c.category}",${c.qty},${c.revenue}`).join("\\n");
      this.triggerDownload(csv, "Sales_By_Category");
    },

    triggerDownload(csv, filename) {
      const blob = new Blob([csv], { type: 'text/csv' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url; a.download = `${filename}.csv`; a.click();
    },
'''

# Patch the load() function to handle new tabs
html_content = html_content.replace(
    "    async load(tabId) {\n      if (!requireAuth() || !requireBranch()) return;\n      this.tab = tabId; this.data = null;",
    "    async load(tabId) {\n      if (!requireAuth() || !requireBranch()) return;\n      this.tab = tabId; this.data = null;\n      if (['tax', 'category'].includes(tabId)) { this.loadCustom(); return; }"
)

html_content = html_content.replace("    async submitJournal() {", new_js_logic + "\n    async submitJournal() {")

html_path.write_text(html_content, encoding="utf-8")
print("✅ Rebuilt reports.html with ZRA Tax and Category tabs")

print("\n🎉 Done! Restart the server.")