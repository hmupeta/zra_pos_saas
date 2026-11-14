import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Rebuild Purchasing Models
# ============================================================
models_path = BACKEND_PATH / "purchasing" / "models.py"
new_models = '''
from django.db import models
from django.conf import settings
from decimal import Decimal

class Supplier(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    tpin = models.CharField(max_length=20, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("tenant", "code")]

    def __str__(self):
        return self.name

    def current_balance(self):
        # Opening Balance + Invoices - Payments
        from django.db.models import Sum
        invs = self.invoices.aggregate(t=Sum('total'))['t'] or 0
        pays = self.payments.aggregate(t=Sum('amount'))['t'] or 0
        return self.opening_balance + invs - pays

class PurchaseOrder(models.Model):
    STATUS = [("DRAFT", "Draft"), ("RECEIVED", "Received"), ("CANCELLED", "Cancelled")]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    po_number = models.CharField(max_length=50, unique=True)
    order_date = models.DateField(auto_now_add=True)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)

    def __str__(self):
        return self.po_number

class SupplierInvoice(models.Model):
    """This is what the supplier gives you to bill you."""
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="invoices")
    invoice_number = models.CharField(max_length=50)
    date = models.DateField(auto_now_add=True)
    due_date = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default="UNPAID") # UNPAID, PAID, PARTIAL

    class Meta:
        unique_together = [("tenant", "invoice_number")]

class SupplierPayment(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="payments")
    invoice = models.ForeignKey(SupplierInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    payment_date = models.DateField(auto_now_add=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=50, default="BANK")
    reference = models.CharField(max_length=100, blank=True)
'''
models_path.write_text(new_models.strip(), encoding="utf-8")
print("✅ Rebuilt purchasing/models.py")

# ============================================================
# 2. Purchasing Views (with Accounting Integration)
# ============================================================
views_path = BACKEND_PATH / "purchasing" / "views.py"
new_views = '''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from .models import Supplier, PurchaseOrder, SupplierInvoice, SupplierPayment
from inventory.models import Product, StockMovement
from accounting.models import Account, Journal, JournalLine

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def suppliers_list(request):
    if request.method == "GET":
        suppliers = Supplier.objects.filter(tenant=request.tenant, is_active=True)
        return Response([{
            "id": s.id, "name": s.name, "phone": s.phone, "balance": float(s.current_balance())
        } for s in suppliers])
        
    data = request.data
    import uuid
    s = Supplier.objects.create(
        tenant=request.tenant, code=f"SUP-{uuid.uuid4().hex[:4].upper()}",
        name=data.get("name"), phone=data.get("phone", ""), email=data.get("email", ""),
        opening_balance=Decimal(str(data.get("opening_balance", 0)))
    )
    return Response({"success": True, "id": s.id})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_invoice(request):
    """Record a supplier invoice and post to accounting"""
    data = request.data
    supplier = Supplier.objects.get(pk=data["supplier_id"], tenant=request.tenant)
    total = Decimal(str(data["total"]))
    
    invoice = SupplierInvoice.objects.create(
        tenant=request.tenant, supplier=supplier,
        invoice_number=data["invoice_number"], total=total
    )

    # Auto-Post to Accounting: Dr Inventory (1200), Cr Accounts Payable (2000)
    inv_account = Account.objects.filter(tenant=request.tenant, code="1200").first()
    ap_account = Account.objects.filter(tenant=request.tenant, code="2000").first()

    if inv_account and ap_account:
        journal = Journal.objects.create(
            tenant=request.tenant, company=request.branch,
            journal_number=f"PINV-{invoice.invoice_number}", date=timezone.now().date(),
            description=f"Supplier Invoice {invoice.invoice_number} - {supplier.name}",
            journal_type="PURCHASE", status="POSTED", created_by=request.user
        )
        JournalLine.objects.create(journal=journal, account=inv_account, debit=total, description="Stock Purchase")
        JournalLine.objects.create(journal=journal, account=ap_account, credit=total, description=f"Owed to {supplier.name}")

    return Response({"success": True, "id": invoice.id})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pay_supplier(request):
    """Record payment to supplier and post to accounting"""
    data = request.data
    supplier = Supplier.objects.get(pk=data["supplier_id"], tenant=request.tenant)
    amount = Decimal(str(data["amount"]))
    invoice_id = data.get("invoice_id")

    invoice = None
    if invoice_id:
        invoice = SupplierInvoice.objects.get(pk=invoice_id, tenant=request.tenant)
        invoice.amount_paid += amount
        invoice.status = "PAID" if invoice.amount_paid >= invoice.total else "PARTIAL"
        invoice.save()

    payment = SupplierPayment.objects.create(
        tenant=request.tenant, supplier=supplier, invoice=invoice,
        amount=amount, method=data.get("method", "BANK"), reference=data.get("reference", "")
    )

    # Auto-Post to Accounting: Dr Accounts Payable (2000), Cr Cash/Bank (1000/1010)
    ap_account = Account.objects.filter(tenant=request.tenant, code="2000").first()
    bank_account = Account.objects.filter(tenant=request.tenant, code="1010").first() # Default to bank

    if ap_account and bank_account:
        journal = Journal.objects.create(
            tenant=request.tenant, company=request.branch,
            journal_number=f"PAY-{payment.id}", date=timezone.now().date(),
            description=f"Payment to {supplier.name}",
            journal_type="PURCHASE", status="POSTED", created_by=request.user
        )
        JournalLine.objects.create(journal=journal, account=ap_account, debit=amount, description="Reduce AP")
        JournalLine.objects.create(journal=journal, account=bank_account, credit=amount, description="Cash Out")

    return Response({"success": True})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def supplier_invoices(request):
    qs = SupplierInvoice.objects.filter(tenant=request.tenant).order_by("-date")
    return Response([{
        "id": i.id, "supplier": i.supplier.name, "invoice_number": i.invoice_number,
        "date": i.date.strftime("%Y-%m-%d"), "total": float(i.total),
        "paid": float(i.amount_paid), "status": i.status
    } for i in qs])
'''
views_path.write_text(new_views.strip(), encoding="utf-8")
print("✅ Rebuilt purchasing/views.py with Auto-Accounting")

# ============================================================
# 3. URLs
# ============================================================
urls_path = BACKEND_PATH / "purchasing" / "urls.py"
new_urls = '''
from django.urls import path
from . import views

urlpatterns = [
    path('suppliers/', views.suppliers_list, name='suppliers_list'),
    path('invoices/', views.supplier_invoices, name='supplier_invoices'),
    path('invoices/create/', views.create_invoice, name='create_invoice'),
    path('pay/', views.pay_supplier, name='pay_supplier'),
]
'''
urls_path.write_text(new_urls.strip(), encoding="utf-8")

# Views Web & URL routing
web_views = BACKEND_PATH / "core" / "views_web.py"
wv_content = web_views.read_text(encoding="utf-8")
if "def purchasing_page" not in wv_content:
    wv_content += "\n\ndef purchasing_page(request):\n    return render(request, 'pos/purchasing.html')\n"
    web_views.write_text(wv_content, encoding="utf-8")

web_urls = BACKEND_PATH / "core" / "urls_web.py"
wu_content = web_urls.read_text(encoding="utf-8")
if "/purchasing" not in wu_content:
    wu_content = wu_content.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('purchasing', views_web.purchasing_page, name='purchasing_page'),"
    )
    web_urls.write_text(wu_content, encoding="utf-8")

# ============================================================
# 4. Frontend UI (Purchasing.html)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "purchasing.html"
html_content = '''
{% extends "pos/base.html" %}
{% block title %}Purchasing & Suppliers{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="purchasingApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Purchasing & Accounts Payable</h1>
      <div class="flex gap-2">
        <button @click="showSupplierModal = true" class="btn-secondary">+ Add Supplier</button>
        <button @click="showInvoiceModal = true" class="btn-primary">+ Record Bill</button>
      </div>
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <!-- Suppliers List -->
      <div class="card p-6">
        <h2 class="font-bold text-lg mb-4">Suppliers</h2>
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-xs uppercase">
            <tr><th class="pb-2">Name</th><th class="pb-2">Phone</th><th class="pb-2 text-right">Balance</th><th class="pb-2 text-right">Action</th></tr>
          </thead>
          <tbody>
            <template x-for="s in suppliers" :key="s.id">
              <tr class="border-t">
                <td class="py-2 font-medium" x-text="s.name"></td>
                <td class="py-2 text-gray-500" x-text="s.phone"></td>
                <td class="py-2 text-right font-bold" :class="s.balance > 0 ? 'text-red-600' : 'text-green-600'" x-text="formatCurrency(s.balance)"></td>
                <td class="py-2 text-right">
                  <button @click="openPayModal(s)" class="text-xs text-brand-600 hover:underline">Pay</button>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>

      <!-- Recent Bills -->
      <div class="card p-6">
        <h2 class="font-bold text-lg mb-4">Recent Bills</h2>
        <table class="w-full text-sm">
          <thead class="bg-gray-50 text-left text-xs uppercase">
            <tr><th class="pb-2">Supplier</th><th class="pb-2">Inv #</th><th class="pb-2 text-right">Total</th><th class="pb-2 text-center">Status</th></tr>
          </thead>
          <tbody>
            <template x-for="i in invoices" :key="i.id">
              <tr class="border-t">
                <td class="py-2 font-medium" x-text="i.supplier"></td>
                <td class="py-2 text-gray-500" x-text="i.invoice_number"></td>
                <td class="py-2 text-right" x-text="formatCurrency(i.total)"></td>
                <td class="py-2 text-center">
                  <span class="px-2 py-0.5 rounded text-xs" :class="i.status === 'PAID' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'" x-text="i.status"></span>
                </td>
              </tr>
            </template>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modals -->
    <template x-if="showSupplierModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-sm w-full p-6">
          <h2 class="text-xl font-bold mb-4">New Supplier</h2>
          <form @submit.prevent="createSupplier()" class="space-y-3">
            <input placeholder="Supplier Name" x-model="supplierForm.name" class="input-field" required>
            <input placeholder="Phone" x-model="supplierForm.phone" class="input-field">
            <input type="number" step="0.01" placeholder="Opening Balance (Owed)" x-model="supplierForm.opening_balance" class="input-field">
            <button type="submit" class="btn-primary w-full">Save Supplier</button>
          </form>
        </div>
      </div>
    </template>

    <template x-if="showInvoiceModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4">Record Supplier Bill</h2>
          <form @submit.prevent="createInvoice()" class="space-y-3">
            <select x-model="invoiceForm.supplier_id" class="input-field" required>
              <option value="">Select Supplier...</option>
              <template x-for="s in suppliers" :key="s.id">
                <option :value="s.id" x-text="s.name"></option>
              </template>
            </select>
            <input placeholder="Invoice Number" x-model="invoiceForm.invoice_number" class="input-field" required>
            <input type="number" step="0.01" placeholder="Total Amount" x-model="invoiceForm.total" class="input-field" required>
            <p class="text-xs text-gray-500">This will increase your stock value and accounts payable.</p>
            <button type="submit" class="btn-primary w-full">Save Bill</button>
          </form>
        </div>
      </div>
    </template>

    <template x-if="payModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-sm w-full p-6">
          <h2 class="text-xl font-bold mb-4" x-text="'Pay ' + payForm.supplier_name"></h2>
          <form @submit.prevent="submitPayment()" class="space-y-3">
            <input type="number" step="0.01" placeholder="Amount to Pay" x-model="payForm.amount" class="input-field" required>
            <select x-model="payForm.method" class="input-field">
              <option value="BANK">Bank Transfer</option>
              <option value="CASH">Cash</option>
            </select>
            <button type="submit" class="btn-primary w-full">Record Payment</button>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function purchasingApp() {
  return {
    suppliers: [], invoices: [],
    showSupplierModal: false, showInvoiceModal: false, payModal: false,
    supplierForm: { name: '', phone: '', opening_balance: 0 },
    invoiceForm: { supplier_id: '', invoice_number: '', total: '' },
    payForm: { supplier_id: '', supplier_name: '', amount: '', method: 'BANK' },

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.suppliers = await apiFetch('/purchasing/suppliers/');
        this.invoices = await apiFetch('/purchasing/invoices/');
      } catch(e) { alert(e.message); }
    },

    async createSupplier() {
      try {
        await apiFetch('/purchasing/suppliers/', { method: 'POST', body: JSON.stringify(this.supplierForm) });
        this.showSupplierModal = false;
        this.supplierForm = { name: '', phone: '', opening_balance: 0 };
        this.load();
      } catch(e) { alert(e.message); }
    },

    async createInvoice() {
      try {
        await apiFetch('/purchasing/invoices/create/', { method: 'POST', body: JSON.stringify(this.invoiceForm) });
        this.showInvoiceModal = false;
        this.invoiceForm = { supplier_id: '', invoice_number: '', total: '' };
        this.load();
      } catch(e) { alert(e.message); }
    },

    openPayModal(s) {
      this.payForm = { supplier_id: s.id, supplier_name: s.name, amount: s.balance, method: 'BANK' };
      this.payModal = true;
    },

    async submitPayment() {
      try {
        await apiFetch('/purchasing/pay/', { method: 'POST', body: JSON.stringify(this.payForm) });
        this.payModal = false;
        this.load();
      } catch(e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(html_content.strip(), encoding="utf-8")
print("✅ Created purchasing.html UI")

# Add to Nav
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")
if "href=\"/purchasing\"" not in nav_content:
    nav_content = nav_content.replace(
        '<a href="/stocktake" class="nav-link"',
        '<a href="/purchasing" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)">Purchasing</a>\n    <a href="/stocktake" class="nav-link"'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Purchasing to Sidebar")

# ============================================================
# 5. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "purchasing"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)
print("\n🎉 Done! Restart the server.")