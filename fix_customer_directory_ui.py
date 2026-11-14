import os
from pathlib import Path
import subprocess
import platform

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Fix Backend View to send Credit fields
# ============================================================
views_path = BACKEND_PATH / "customers" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

new_list_view = '''
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def customers_list(request):
    if request.method == "GET":
        q = request.query_params.get("search", "")
        qs = Customer.objects.filter(tenant=request.tenant).order_by("-total_spent")
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone_number__icontains=q))
            
        return Response([{
            "id": c.id, "name": c.full_name, "phone": c.phone_number,
            "loyalty_points": float(c.loyalty_points), "total_spent": float(c.total_spent),
            "credit_limit": float(c.credit_limit), "account_balance": float(c.account_balance)
        } for c in qs[:50]])
        
    # POST: Quick Create from POS
    data = request.data
    phone = data.get("phone_number")
    if Customer.objects.filter(tenant=request.tenant, phone_number=phone).exists():
        return Response({"error": "Phone number already registered"}, status=400)
        
    import uuid
    c = Customer.objects.create(
        tenant=request.tenant, company=request.branch,
        customer_id=f"CUST{uuid.uuid4().hex[:6].upper()}",
        first_name=data.get("first_name", "Walk-in"),
        last_name=data.get("last_name", ""),
        phone_number=phone,
        email=data.get("email", ""),
        credit_limit=data.get("credit_limit", 0)
    )
    return Response({"success": True, "id": c.id, "name": c.full_name})
'''

import re
pattern = r"@api_view\(\[\"GET\", \"POST\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef customers_list\(request\):.*?return Response\(\{\"success\": True, \"id\": c\.id, \"name\": c\.full_name\}\)"
if re.search(pattern, v_content, flags=re.DOTALL):
    v_content = re.sub(pattern, new_list_view.strip(), v_content, flags=re.DOTALL)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Backend updated to include credit_limit and account_balance.")
else:
    print("⚠️ Could not match backend view. Checking manually.")

# ============================================================
# 2. Rebuild customers.html
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "customers.html"
full_html = '''
{% extends "pos/base.html" %}
{% block title %}Customers{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="customersApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Customer Directory</h1>
        <p class="text-gray-500 text-sm mt-1">Manage customers, loyalty points, and credit limits.</p>
      </div>
      <div class="flex gap-2">
        <button @click="exportCsv()" class="btn-secondary text-sm">Export CSV</button>
        <button @click="showModal = true" class="btn-primary">+ Add Customer</button>
      </div>
    </div>

    <div class="mb-4">
      <input type="text" x-model="search" @input.debounce.300ms="load()" placeholder="Search by name or phone number..." class="input-field max-w-md">
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Customer Name</th>
            <th class="px-4 py-3">Phone Number</th>
            <th class="px-4 py-3 text-right">Total Spent</th>
            <th class="px-4 py-3 text-right">Credit Limit</th>
            <th class="px-4 py-3 text-right">Owed (AR)</th>
            <th class="px-4 py-3 text-right">Loyalty Points</th>
            <th class="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="c in customers" :key="c.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-medium text-slate-800" x-text="c.name"></td>
              <td class="px-4 py-3 text-gray-600" x-text="c.phone"></td>
              <td class="px-4 py-3 text-right font-bold" x-text="formatCurrency(c.total_spent)"></td>
              <td class="px-4 py-3 text-right text-gray-600" x-text="formatCurrency(c.credit_limit)"></td>
              <td class="px-4 py-3 text-right font-bold" :class="c.account_balance > 0 ? 'text-red-600' : 'text-green-600'" x-text="formatCurrency(c.account_balance)"></td>
              <td class="px-4 py-3 text-right">
                <span class="bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full text-xs font-bold" x-text="c.loyalty_points + ' pts'"></span>
              </td>
              <td class="px-4 py-3 text-right space-x-2">
                <button @click="viewDetails(c)" class="text-brand-600 hover:underline text-xs font-medium">View</button>
                <button x-show="c.account_balance > 0" @click="openPayModal(c)" class="text-green-600 hover:underline text-xs font-bold">Receive Payment</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="customers.length === 0" class="p-8 text-center text-gray-400">
        <i data-lucide="users" class="w-12 h-12 mx-auto mb-2 opacity-30"></i>
        <p>No customers found. Click "+ Add Customer" to create one.</p>
      </div>
    </div>

    <!-- Add Customer Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-[9999] p-4" @click.self="showModal = false">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4">New Customer</h2>
          <form @submit.prevent="createCustomer()" class="space-y-3">
            <input placeholder="Phone Number" x-model="form.phone_number" class="input-field" required>
            <input placeholder="First Name" x-model="form.first_name" class="input-field" required>
            <input placeholder="Last Name (Optional)" x-model="form.last_name" class="input-field">
            <input type="email" placeholder="Email (Optional)" x-model="form.email" class="input-field">
            <input type="number" step="0.01" placeholder="Credit Limit (K)" x-model="form.credit_limit" class="input-field" value="0">
            <div class="flex gap-2 mt-4">
              <button type="button" @click="showModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1">Save Customer</button>
            </div>
          </form>
        </div>
      </div>
    </template>

    <!-- View Customer Modal -->
    <template x-if="selectedCust">
      <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[9000] p-4 backdrop-blur-sm" @click.self="selectedCust = null">
        <div class="bg-white rounded-xl max-w-md w-full p-6 shadow-2xl">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold" x-text="selectedCust.name"></h2>
            <button @click="selectedCust = null" class="text-gray-400 hover:text-gray-600 text-2xl font-bold">&times;</button>
          </div>
          <div class="space-y-3 text-sm">
            <div class="flex justify-between border-b pb-2"><span class="text-gray-500">Phone:</span><span class="font-medium" x-text="selectedCust.phone"></span></div>
            <div class="flex justify-between border-b pb-2"><span class="text-gray-500">Lifetime Spend:</span><span class="font-bold text-brand-700" x-text="formatCurrency(selectedCust.total_spent)"></span></div>
            <div class="flex justify-between border-b pb-2"><span class="text-gray-500">Loyalty Points:</span><span class="font-bold text-yellow-600" x-text="selectedCust.loyalty_points"></span></div>
            <div class="flex justify-between border-b pb-2"><span class="text-gray-500">Credit Limit:</span><span class="font-medium" x-text="formatCurrency(selectedCust.credit_limit)"></span></div>
            <div class="flex justify-between border-b pb-2"><span class="text-gray-500">Outstanding Debt:</span><span class="font-bold" :class="selectedCust.account_balance > 0 ? 'text-red-600' : 'text-green-600'" x-text="formatCurrency(selectedCust.account_balance)"></span></div>
          </div>
        </div>
      </div>
    </template>

    <!-- Receive Payment Modal -->
    <template x-if="payModalCust">
      <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[9999] p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl max-w-sm w-full p-6">
          <h2 class="text-xl font-bold mb-2">Receive Payment</h2>
          <p class="text-sm text-gray-500 mb-4">From: <span class="font-bold text-gray-800" x-text="payModalCust.name"></span></p>
          
          <div class="bg-red-50 text-red-800 p-3 rounded mb-4 text-sm flex justify-between font-bold border border-red-100">
            <span>Outstanding Balance:</span>
            <span x-text="formatCurrency(payModalCust.account_balance)"></span>
          </div>

          <form @submit.prevent="submitPayment()" class="space-y-4">
            <div>
              <label class="block text-sm mb-1">Amount Received (K)</label>
              <input type="number" step="0.01" x-model="payAmount" class="input-field text-lg font-bold" required>
            </div>
            <div class="flex gap-2">
              <button type="button" @click="payModalCust = null" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1 bg-green-600 hover:bg-green-700">Record Payment</button>
            </div>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>

<script>
function customersApp() {
  return {
    customers: [], search: '', showModal: false, selectedCust: null,
    payModalCust: null, payAmount: 0,
    form: { first_name: '', last_name: '', phone_number: '', email: '', credit_limit: 0 },

    async load() {
      if (!requireAuth()) return;
      try {
        this.customers = await apiFetch(`/customers/?search=${this.search}`);
        setTimeout(() => { lucide.createIcons(); }, 50);
      } catch (e) { alert(e.message); }
    },

    async createCustomer() {
      try {
        await apiFetch('/customers/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        this.form = { first_name: '', last_name: '', phone_number: '', email: '', credit_limit: 0 };
        this.load();
      } catch (e) { alert(e.response?.data?.error || e.message); }
    },

    viewDetails(c) {
      this.selectedCust = c;
    },

    openPayModal(c) {
      this.payModalCust = c;
      this.payAmount = c.account_balance;
    },

    async submitPayment() {
      try {
        const res = await apiFetch('/customers/pay/', {
          method: 'POST',
          body: JSON.stringify({ customer_id: this.payModalCust.id, amount: this.payAmount })
        });
        alert('Payment recorded successfully!');
        this.payModalCust = null;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },

    async exportCsv() {
      try {
        const res = await fetch('/api/auth/export/customers/', {
          headers: { 'Authorization': `Token ${localStorage.getItem('token')}` }
        });
        if (!res.ok) throw new Error('Export failed');
        const blob = await res.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url; a.download = 'customers.csv'; a.click();
      } catch (e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(full_html.strip(), encoding="utf-8")
print("✅ Rebuilt customers.html completely with working search and tables.")

# ============================================================
# 3. Re-seed customers if they are missing
# ============================================================
print("\nChecking for existing customers...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

seed_script = """
from core.models import User, Company
from customers.models import Customer
from decimal import Decimal

tenant = User.objects.get(username='demo_owner').tenant
branch = Company.objects.filter(tenant=tenant).first()

if Customer.objects.filter(tenant=tenant).count() == 0:
    customers_data = [
        ("CUST0001", "Mary", "Phiri", "+260971111111", "mary@example.com", 150),
        ("CUST0002", "John", "Banda", "+260972222222", "john@example.com", 320),
        ("CUST0003", "Grace", "Mulenga", "+260973333333", "grace@example.com", 85),
    ]
    for cid, first, last, phone, email, points in customers_data:
        Customer.objects.create(
            tenant=tenant, company=branch, customer_id=cid,
            first_name=first, last_name=last, phone_number=phone, email=email,
            loyalty_points=Decimal(str(points)), kyc_status="PENDING"
        )
    print("✅ Re-seeded 3 sample customers.")
else:
    print(f"✅ Customers already exist: {Customer.objects.filter(tenant=tenant).count()}")
"""

seed_file = BACKEND_PATH / "_seed_customers.py"
seed_file.write_text(seed_script, encoding="utf-8")
subprocess.run([str(python), "manage.py", "shell", "-c", f"exec(open('{seed_file.name}', encoding='utf-8').read())"], cwd=BACKEND_PATH)
seed_file.unlink()

print("\n🎉 Done! Restart the server and do a HARD REFRESH on the Customers page.")