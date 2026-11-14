import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Backend Views for Platform Billing
# ============================================================
saas_views = BACKEND_PATH / "saas" / "views.py"
content = saas_views.read_text(encoding="utf-8")

billing_views = '''
from datetime import date, timedelta
from decimal import Decimal
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import TenantInvoice, TenantPayment
from core.models import Tenant
from .permissions import IsPlatformAdmin

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def platform_invoices(request):
    if request.method == "GET":
        qs = TenantInvoice.objects.select_related("tenant").order_by("-invoice_date")
        return Response([{
            "id": i.id, "invoice_number": i.invoice_number,
            "tenant_name": i.tenant.name, "tenant_id": i.tenant.id,
            "date": i.invoice_date.strftime("%Y-%m-%d"),
            "due_date": i.due_date.strftime("%Y-%m-%d"),
            "total": float(i.total), "amount_paid": float(i.amount_paid),
            "balance": float(i.total - i.amount_paid),
            "status": i.status
        } for i in qs])

    # POST: Create Invoice
    data = request.data
    tenant_id = data.get("tenant_id")
    try:
        tenant = Tenant.objects.get(pk=tenant_id)
    except Tenant.DoesNotExist:
        return Response({"error": "Tenant not found"}, status=404)

    import uuid
    inv_num = f"SaaS-{uuid.uuid4().hex[:6].upper()}"
    amount = Decimal(str(data.get("amount", 0)))
    
    invoice = TenantInvoice.objects.create(
        tenant=tenant, invoice_number=inv_num,
        invoice_date=date.today(), due_date=date.today() + timedelta(days=14),
        description=f"Subscription - {tenant.plan.name if tenant.plan else 'Custom'}",
        subtotal=amount, tax_amount=0, total=amount, status="SENT"
    )
    return Response({"success": True, "id": invoice.id})

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def platform_payments(request):
    if request.method == "GET":
        qs = TenantPayment.objects.select_related("tenant", "invoice").order_by("-payment_date")
        return Response([{
            "id": p.id, "tenant_name": p.tenant.name,
            "invoice_number": p.invoice.invoice_number if p.invoice else "N/A",
            "date": p.payment_date.strftime("%Y-%m-%d"),
            "amount": float(p.amount), "method": p.payment_method,
            "reference": p.reference
        } for p in qs])

    # POST: Record Payment
    data = request.data
    invoice_id = data.get("invoice_id")
    amount = Decimal(str(data.get("amount", 0)))
    
    try:
        invoice = TenantInvoice.objects.get(pk=invoice_id)
    except TenantInvoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    payment = TenantPayment.objects.create(
        tenant=invoice.tenant, invoice=invoice,
        payment_number=f"PAY-{invoice.invoice_number}-{invoice.payments.count() + 1}",
        payment_date=date.today(), amount=amount,
        payment_method=data.get("method", "BANK"),
        reference=data.get("reference", "")
    )

    # Update Invoice Status
    invoice.amount_paid += amount
    if invoice.amount_paid >= invoice.total:
        invoice.status = "PAID"
        invoice.paid_at = timezone.now()
        invoice.tenant.subscription_status = "ACTIVE"
        invoice.tenant.save()
    invoice.save()

    return Response({"success": True})
'''

if "def platform_invoices" not in content:
    saas_views.write_text(content + "\n\n" + billing_views, encoding="utf-8")

# Update URLs
saas_urls = BACKEND_PATH / "saas" / "urls.py"
u_content = saas_urls.read_text(encoding="utf-8")
if "platform_invoices" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path("admin/billing/invoices/", views.platform_invoices, name="platform_invoices"),
    path("admin/billing/payments/", views.platform_payments, name="platform_payments"),'''
    )
    saas_urls.write_text(u_content, encoding="utf-8")
print("✅ Added SaaS Billing API")

# ============================================================
# 2. Add Frontend Route
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")
if "def platform_billing_page" not in web_content:
    web_content += "\n\ndef platform_billing_page(request):\n    return render(request, 'pos/platform_billing.html')\n"
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/platform/billing" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('platform/billing', views_web.platform_billing_page, name='platform_billing'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")
print("✅ Added Platform Billing Route")

# ============================================================
# 3. Create Billing UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "platform_billing.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}SaaS Billing - Platform Admin{% endblock %}
{% block body %}
<div class="h-screen flex bg-slate-50">
  <!-- Sidebar -->
  <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col shadow-2xl z-20">
    <div class="h-16 flex items-center px-6 border-b border-slate-800 bg-slate-950/50">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center text-white shadow-lg"><i data-lucide="shield" class="w-5 h-5"></i></div>
        <div><div class="font-bold text-white tracking-wide text-lg">Nimbus HQ</div><div class="text-[10px] text-slate-400 uppercase tracking-wider">Platform Admin</div></div>
      </div>
    </div>
    <nav class="flex-1 py-6 px-4 space-y-1">
      <a href="/platform" class="nav-link"><i data-lucide="layout-dashboard" class="w-4 h-4 mr-3"></i> Overview</a>
      <a href="/platform/tenants" class="nav-link"><i data-lucide="building" class="w-4 h-4 mr-3"></i> Tenants</a>
      <a href="/platform/applications" class="nav-link"><i data-lucide="file-text" class="w-4 h-4 mr-3"></i> Applications</a>
      <a href="/platform/billing" class="nav-link active"><i data-lucide="credit-card" class="w-4 h-4 mr-3"></i> Billing</a>
    </nav>
  </aside>

  <div class="flex-1 overflow-y-auto p-8" x-data="billingPage()" x-init="load()">
    <div class="flex justify-between items-center mb-8">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">SaaS Billing</h1>
        <p class="text-slate-500 mt-1">Manage subscriptions and invoices for your tenants.</p>
      </div>
      <div class="flex gap-2">
        <button @click="showPaymentModal = true" class="btn-secondary">Record Payment</button>
        <button @click="showInvoiceModal = true" class="btn-primary">+ Generate Invoice</button>
      </div>
    </div>

    <!-- Tabs -->
    <div class="flex gap-2 mb-6 border-b border-gray-200">
      <button @click="tab = 'invoices'" :class="tab === 'invoices' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500'" class="px-4 py-2 font-medium">Invoices</button>
      <button @click="tab = 'payments'" :class="tab === 'payments' ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500'" class="px-4 py-2 font-medium">Payments</button>
    </div>

    <!-- Invoices Table -->
    <div x-show="tab === 'invoices'" class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-6 py-4">Invoice #</th>
            <th class="px-6 py-4">Tenant</th>
            <th class="px-6 py-4">Due Date</th>
            <th class="px-6 py-4 text-right">Total</th>
            <th class="px-6 py-4 text-right">Balance</th>
            <th class="px-6 py-4 text-center">Status</th>
            <th class="px-6 py-4 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="i in invoices" :key="i.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-6 py-4 font-mono text-xs" x-text="i.invoice_number"></td>
              <td class="px-6 py-4 font-bold text-slate-900" x-text="i.tenant_name"></td>
              <td class="px-6 py-4 text-gray-500" x-text="i.due_date"></td>
              <td class="px-6 py-4 text-right" x-text="formatCurrency(i.total)"></td>
              <td class="px-6 py-4 text-right font-bold text-red-600" x-text="formatCurrency(i.balance)"></td>
              <td class="px-6 py-4 text-center">
                <span class="px-2 py-1 rounded text-xs font-bold" :class="i.status === 'PAID' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'" x-text="i.status"></span>
              </td>
              <td class="px-6 py-4 text-right">
                <button x-show="i.status !== 'PAID'" @click="openPayment(i)" class="text-brand-600 hover:underline text-xs">Pay</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Payments Table -->
    <div x-show="tab === 'payments'" class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-6 py-4">Date</th>
            <th class="px-6 py-4">Tenant</th>
            <th class="px-6 py-4">Invoice</th>
            <th class="px-6 py-4">Method</th>
            <th class="px-6 py-4 text-right">Amount</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="p in payments" :key="p.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-6 py-4 text-gray-500" x-text="p.date"></td>
              <td class="px-6 py-4 font-bold text-slate-900" x-text="p.tenant_name"></td>
              <td class="px-6 py-4 font-mono text-xs" x-text="p.invoice_number"></td>
              <td class="px-6 py-4"><span class="bg-gray-100 px-2 py-0.5 rounded text-xs" x-text="p.method"></span></td>
              <td class="px-6 py-4 text-right font-bold text-green-600" x-text="formatCurrency(p.amount)"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Generate Invoice Modal -->
    <template x-if="showInvoiceModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4">Generate SaaS Invoice</h2>
          <form @submit.prevent="createInvoice()" class="space-y-4">
            <div>
              <label class="block text-sm mb-1">Select Tenant</label>
              <select x-model="invoiceForm.tenant_id" @change="setInvoiceAmount" class="input-field" required>
                <option value="">Select Tenant...</option>
                <template x-for="t in tenants" :key="t.id">
                  <option :value="t.id" x-text="t.name + ' (' + t.plan + ')'"></option>
                </template>
              </select>
            </div>
            <div>
              <label class="block text-sm mb-1">Amount (K)</label>
              <input type="number" step="0.01" x-model="invoiceForm.amount" class="input-field font-bold" required>
            </div>
            <button type="submit" class="btn-primary w-full">Create Invoice</button>
          </form>
        </div>
      </div>
    </template>

    <!-- Record Payment Modal -->
    <template x-if="showPaymentModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4">Record Payment</h2>
          <form @submit.prevent="submitPayment()" class="space-y-4">
            <div>
              <label class="block text-sm mb-1">Select Invoice</label>
              <select x-model="paymentForm.invoice_id" @change="setPaymentAmount" class="input-field" required>
                <option value="">Select Unpaid Invoice...</option>
                <template x-for="i in invoices.filter(x => x.status !== 'PAID')" :key="i.id">
                  <option :value="i.id" x-text="i.invoice_number + ' - ' + i.tenant_name + ' (' + formatCurrency(i.balance) + ')'"></option>
                </template>
              </select>
            </div>
            <div>
              <label class="block text-sm mb-1">Amount Received (K)</label>
              <input type="number" step="0.01" x-model="paymentForm.amount" class="input-field font-bold" required>
            </div>
            <div>
              <label class="block text-sm mb-1">Payment Method</label>
              <select x-model="paymentForm.method" class="input-field">
                <option value="BANK">Bank Transfer</option>
                <option value="CASH">Cash</option>
                <option value="MOMO">Mobile Money</option>
              </select>
            </div>
            <button type="submit" class="btn-primary w-full bg-green-600 hover:bg-green-700">Record Payment</button>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function billingPage() {
  return {
    tab: 'invoices', invoices: [], payments: [], tenants: [],
    showInvoiceModal: false, showPaymentModal: false,
    invoiceForm: { tenant_id: '', amount: 0 },
    paymentForm: { invoice_id: '', amount: 0, method: 'BANK' },

    async load() {
      if (!requireAuth()) return;
      if (getUser()?.user_type !== 'PLATFORM_ADMIN') { location.href = '/pos'; return; }
      try {
        this.invoices = await apiFetch('/saas/admin/billing/invoices/');
        this.payments = await apiFetch('/saas/admin/billing/payments/');
        this.tenants = await apiFetch('/saas/admin/tenants/');
      } catch(e) { alert(e.message); }
    },

    setInvoiceAmount() {
      const t = this.tenants.find(x => x.id == this.invoiceForm.tenant_id);
      if (t) this.invoiceForm.amount = t.monthly_price;
    },

    setPaymentAmount() {
      const i = this.invoices.find(x => x.id == this.paymentForm.invoice_id);
      if (i) this.paymentForm.amount = i.balance;
    },

    async createInvoice() {
      try {
        await apiFetch('/saas/admin/billing/invoices/', { method: 'POST', body: JSON.stringify(this.invoiceForm) });
        this.showInvoiceModal = false;
        this.load();
      } catch(e) { alert(e.message); }
    },

    async submitPayment() {
      try {
        await apiFetch('/saas/admin/billing/payments/', { method: 'POST', body: JSON.stringify(this.paymentForm) });
        this.showPaymentModal = false;
        this.load();
      } catch(e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created platform_billing.html UI")

print("\n🎉 Done! Restart the server.")