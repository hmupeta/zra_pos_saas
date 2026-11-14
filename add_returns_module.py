import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Rebuild Returns Models
# ============================================================
models_path = BACKEND_PATH / "returns" / "models.py"
new_models = '''
from django.db import models
from django.conf import settings

class ReturnRequest(models.Model):
    STATUS = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    invoice = models.ForeignKey("sales.Invoice", on_delete=models.PROTECT, related_name="returns")
    return_number = models.CharField(max_length=50, unique=True)
    reason = models.CharField(max_length=100, default="Customer Request")
    refund_method = models.CharField(max_length=50, default="CASH") # CASH, STORE_CREDIT
    total_refund = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="COMPLETED")
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.return_number

class ReturnItem(models.Model):
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="items")
    invoice_item = models.ForeignKey("sales.InvoiceItem", on_delete=models.PROTECT)
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    quantity_returned = models.DecimalField(max_digits=10, decimal_places=2)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    restock = models.BooleanField(default=True)
'''
models_path.write_text(new_models.strip(), encoding="utf-8")
print("✅ Rebuilt returns/models.py")

# ============================================================
# 2. Returns Views (with Accounting & Inventory Reversal)
# ============================================================
views_path = BACKEND_PATH / "returns" / "views.py"
new_views = '''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.utils import timezone
import datetime
from sales.models import Invoice, InvoiceItem
from inventory.models import Product, StockMovement
from inventory.services import BarcodeService
from accounting.models import Account, Journal, JournalLine
from .models import ReturnRequest, ReturnItem

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_invoice(request):
    query = request.query_params.get("q", "")
    if not query:
        return Response([])
    
    qs = Invoice.objects.filter(tenant=request.tenant, status="PAID").filter(
        invoice_number__icontains=query
    )[:5]
    
    return Response([{
        "id": i.id, "invoice_number": i.invoice_number,
        "date": i.created_at.strftime("%Y-%m-%d"),
        "total": float(i.total), "customer": i.customer_name
    } for i in qs])

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invoice_details(request, pk):
    try:
        inv = Invoice.objects.get(pk=pk, tenant=request.tenant)
    except Invoice.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
        
    return Response({
        "id": inv.id, "invoice_number": inv.invoice_number,
        "items": [{
            "id": i.id, "name": i.product.name, "barcode": i.product.barcode,
            "qty_sold": float(i.quantity), "price": float(i.unit_price),
            "tax_rate": float(i.tax_rate), "total": float(i.total)
        } for i in inv.items.all()]
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_return(request):
    data = request.data
    invoice_id = data.get("invoice_id")
    items_data = data.get("items", [])
    
    try:
        invoice = Invoice.objects.get(pk=invoice_id, tenant=request.tenant)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    if not items_data:
        return Response({"error": "No items selected for return"}, status=400)

    # Generate Return Number
    ref = f"RTN-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
    total_refund = Decimal("0")

    ret = ReturnRequest.objects.create(
        tenant=request.tenant, company=request.branch,
        invoice=invoice, return_number=ref, refund_method=data.get("refund_method", "CASH"),
        processed_by=request.user
    )

    for item in items_data:
        inv_item = InvoiceItem.objects.get(pk=item["invoice_item_id"])
        qty = Decimal(str(item["quantity"]))
        refund_amount = qty * inv_item.unit_price
        total_refund += refund_amount
        
        restock = item.get("restock", True)

        # 1. Create Return Item
        ReturnItem.objects.create(
            return_request=ret, invoice_item=inv_item, product=inv_item.product,
            quantity_returned=qty, refund_amount=refund_amount, restock=restock
        )

        # 2. Restock Inventory (if required)
        if restock:
            product = Product.objects.select_for_update().get(pk=inv_item.product.id)
            product.current_stock += qty
            product.save()
            
            StockMovement.objects.create(
                product=product, quantity=qty, movement_type="IN",
                reference=ref, notes="Customer Return", created_by=request.user
            )
            BarcodeService.invalidate_product(product)

    ret.total_refund = total_refund
    ret.save()

    # 3. Reverse Accounting
    # Dr Sales Returns (4010), Dr VAT Payable (2100), Cr Cash (1000)
    sales_returns = Account.objects.filter(tenant=request.tenant, code="4010").first()
    vat_account = Account.objects.filter(tenant=request.tenant, code="2100").first()
    cash_account = Account.objects.filter(tenant=request.tenant, code="1000").first()

    if sales_returns and vat_account and cash_account:
        # Calculate VAT portion (16% inclusive)
        net_amount = total_refund / Decimal("1.16")
        tax_amount = total_refund - net_amount

        journal = Journal.objects.create(
            tenant=request.tenant, company=request.branch,
            journal_number=f"REF-{ref}", date=timezone.now().date(),
            description=f"Refund for {invoice.invoice_number}",
            journal_type="ADJUSTMENT", status="POSTED", created_by=request.user
        )
        
        # Dr Sales Returns (Contra-Revenue)
        JournalLine.objects.create(journal=journal, account=sales_returns, debit=net_amount, description=f"Return {ref}")
        # Dr VAT Payable (we get VAT back from ZRA)
        JournalLine.objects.create(journal=journal, account=vat_account, debit=tax_amount, description=f"VAT Reversal {ref}")
        # Cr Cash (we paid out cash)
        JournalLine.objects.create(journal=journal, account=cash_account, credit=total_refund, description=f"Refund Payout {ref}")

    return Response({
        "success": True, "return_number": ref, "total_refund": float(total_refund)
    })
'''
views_path.write_text(new_views.strip(), encoding="utf-8")
print("✅ Rebuilt returns/views.py with Auto-Accounting & Stock Restocking")

# URLs
urls_path = BACKEND_PATH / "returns" / "urls.py"
new_urls = '''
from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search_invoice, name='search_invoice'),
    path('invoice/<int:pk>/', views.invoice_details, name='invoice_details'),
    path('process/', views.process_return, name='process_return'),
]
'''
urls_path.write_text(new_urls.strip(), encoding="utf-8")
print("✅ Updated returns/urls.py")

# ============================================================
# 3. Add Route & Navigation
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")
if "def returns_page" not in web_content:
    web_content += "\n\ndef returns_page(request):\n    return render(request, 'pos/returns.html')\n"
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/returns" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('returns', views_web.returns_page, name='returns_page'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")
if "href=\"/returns\"" not in nav_content:
    # Place it under Invoices
    nav_content = nav_content.replace(
        '<a href="/invoices" class="nav-link">Invoices</a>',
        '<a href="/invoices" class="nav-link">Invoices</a>\n    <a href="/returns" class="nav-link">Returns</a>'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Returns to Sidebar")

# ============================================================
# 4. Create Returns UI (HTML)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "returns.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Returns{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="returnsApp()">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Returns & Refunds</h1>
    </div>

    <!-- Search Section -->
    <div class="card p-6 mb-6" x-show="!selectedInvoice">
      <label class="block text-sm font-medium mb-2">Search by Invoice Number</label>
      <div class="flex gap-2">
        <input type="text" x-model="searchQuery" @input.debounce.300ms="searchInvoices()" placeholder="e.g. 261113111140" class="input-field max-w-md">
      </div>
      
      <div class="mt-4 space-y-2">
        <template x-for="inv in searchResults" :key="inv.id">
          <div @click="openInvoice(inv.id)" class="p-3 bg-gray-50 border rounded cursor-pointer hover:bg-gray-100 flex justify-between">
            <div>
              <span class="font-bold" x-text="inv.invoice_number"></span>
              <span class="text-sm text-gray-500 ml-2" x-text="inv.date"></span>
            </div>
            <div class="font-semibold" x-text="formatCurrency(inv.total)"></div>
          </div>
        </template>
        <div x-show="searchQuery.length > 0 && searchResults.length === 0" class="text-gray-500 text-sm mt-2">No invoices found.</div>
      </div>
    </div>

    <!-- Return Processing Section -->
    <div class="card p-6" x-show="selectedInvoice" x-cloak>
      <div class="flex justify-between items-center mb-4 border-b pb-4">
        <div>
          <h2 class="text-xl font-bold" x-text="'Invoice: ' + selectedInvoice?.invoice_number"></h2>
          <p class="text-sm text-gray-500">Select the items and quantities the customer is returning.</p>
        </div>
        <button @click="selectedInvoice = null" class="text-sm text-gray-500 hover:underline">Cancel</button>
      </div>

      <table class="w-full text-sm mb-6">
        <thead class="bg-gray-50 text-left text-xs uppercase">
          <tr><th class="p-2">Item</th><th class="p-2">Price</th><th class="p-2">Qty Sold</th><th class="p-2">Return Qty</th><th class="p-2 text-center">Restock?</th></tr>
        </thead>
        <tbody>
          <template x-for="item in selectedInvoice.items" :key="item.id">
            <tr class="border-t">
              <td class="p-2 font-medium" x-text="item.name"></td>
              <td class="p-2" x-text="formatCurrency(item.price)"></td>
              <td class="p-2" x-text="item.qty_sold"></td>
              <td class="p-2">
                <input type="number" step="0.01" min="0" :max="item.qty_sold" x-model.number="returnQtys[item.id]" class="input-field w-24 py-1 text-sm">
              </td>
              <td class="p-2 text-center">
                <input type="checkbox" x-model="restockFlags[item.id]" class="w-4 h-4 text-brand-600 rounded">
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <div class="flex justify-end items-center gap-4 border-t pt-4">
        <div class="text-right">
          <div class="text-sm text-gray-500">Total Refund Amount</div>
          <div class="text-2xl font-bold text-red-600" x-text="formatCurrency(calculateRefundTotal())"></div>
        </div>
        <button @click="processReturn()" class="btn-primary bg-red-600 hover:bg-red-700" :disabled="calculateRefundTotal() === 0">Process Refund</button>
      </div>
    </div>

  </div>
</div>
<script>
function returnsApp() {
  return {
    searchQuery: '', searchResults: [], selectedInvoice: null,
    returnQtys: {}, restockFlags: {},

    async searchInvoices() {
      if (this.searchQuery.length < 2) { this.searchResults = []; return; }
      try {
        this.searchResults = await apiFetch(`/returns/search/?q=${this.searchQuery}`);
      } catch (e) { alert(e.message); }
    },

    async openInvoice(id) {
      try {
        this.selectedInvoice = await apiFetch(`/returns/invoice/${id}/`);
        this.returnQtys = {};
        this.restockFlags = {};
        // Initialize defaults
        this.selectedInvoice.items.forEach(i => {
          this.returnQtys[i.id] = 0;
          this.restockFlags[i.id] = true;
        });
      } catch (e) { alert(e.message); }
    },

    calculateRefundTotal() {
      if (!this.selectedInvoice) return 0;
      let total = 0;
      this.selectedInvoice.items.forEach(i => {
        const qty = this.returnQtys[i.id] || 0;
        total += qty * i.price;
      });
      return total;
    },

    async processReturn() {
      if (!confirm('Are you sure you want to process this refund? This will restock inventory and adjust the accounting books.')) return;
      
      const itemsToReturn = [];
      this.selectedInvoice.items.forEach(i => {
        const qty = this.returnQtys[i.id] || 0;
        if (qty > 0) {
          itemsToReturn.push({
            invoice_item_id: i.id,
            quantity: qty,
            restock: this.restockFlags[i.id]
          });
        }
      });

      try {
        const res = await apiFetch('/returns/process/', {
          method: 'POST',
          body: JSON.stringify({ 
            invoice_id: this.selectedInvoice.id,
            items: itemsToReturn,
            refund_method: 'CASH'
          })
        });
        alert(`Refund Processed Successfully!\\nRef: ${res.return_number}\\nAmount: ${formatCurrency(res.total_refund)}`);
        this.selectedInvoice = null;
        this.searchQuery = '';
        this.searchResults = [];
      } catch (e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created returns.html UI")

# ============================================================
# 5. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "returns"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")