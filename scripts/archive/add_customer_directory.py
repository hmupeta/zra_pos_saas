import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add view and URL for the Customers page
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
content = views_web.read_text(encoding="utf-8")
if "def customers_page" not in content:
    content += "\n\ndef customers_page(request):\n    return render(request, 'pos/customers.html')\n"
    views_web.write_text(content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
url_content = urls_web.read_text(encoding="utf-8")
if "/customers" not in url_content:
    url_content = url_content.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('customers', views_web.customers_page, name='customers_page'),"
    )
    urls_web.write_text(url_content, encoding="utf-8")
print("✅ Added Customers route to core/urls_web.py")

# ============================================================
# 2. Add "Customers" to the Sidebar Navigation
# ============================================================
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")

if "href=\"/customers\"" not in nav_content:
    # We'll place it right under "Invoices"
    nav_content = nav_content.replace(
        '<a href="/invoices" class="nav-link">Invoices</a>',
        '<a href="/invoices" class="nav-link">Invoices</a>\n    <a href="/customers" class="nav-link">Customers</a>'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Customers link to Sidebar")

# ============================================================
# 3. Create the Customers HTML UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "customers.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Customers{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="customersApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Customer Directory</h1>
      <button @click="showModal = true" class="btn-primary">+ Add Customer</button>
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
            <th class="px-4 py-3 text-right">Loyalty Points</th>
            <th class="px-4 py-3 text-right">Action</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="c in customers" :key="c.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-medium" x-text="c.name"></td>
              <td class="px-4 py-3 text-gray-600" x-text="c.phone"></td>
              <td class="px-4 py-3 text-right font-bold" x-text="formatCurrency(c.total_spent)"></td>
              <td class="px-4 py-3 text-right">
                <span class="bg-yellow-100 text-yellow-800 px-2 py-0.5 rounded-full text-xs font-bold" x-text="c.loyalty_points + ' pts'"></span>
              </td>
              <td class="px-4 py-3 text-right">
                <button @click="viewDetails(c)" class="text-brand-600 hover:underline text-xs">View</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="customers.length === 0" class="p-8 text-center text-gray-400">No customers found.</div>
    </div>

    <!-- Add Customer Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-sm w-full p-6">
          <h2 class="text-xl font-bold mb-4">New Customer</h2>
          <form @submit.prevent="createCustomer()" class="space-y-3">
            <input placeholder="Phone Number" x-model="form.phone_number" class="input-field" required>
            <input placeholder="First Name" x-model="form.first_name" class="input-field" required>
            <input placeholder="Last Name (Optional)" x-model="form.last_name" class="input-field">
            <input type="email" placeholder="Email (Optional)" x-model="form.email" class="input-field">
            <button type="submit" class="btn-primary w-full">Save Customer</button>
          </form>
        </div>
      </div>
    </template>

    <!-- View Customer Modal -->
    <template x-if="selectedCust">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold" x-text="selectedCust.name"></h2>
            <button @click="selectedCust = null" class="text-gray-400 hover:text-gray-600">✕</button>
          </div>
          <div class="space-y-3 text-sm">
            <div class="flex justify-between border-b pb-2"><span class="text-gray-500">Phone:</span><span class="font-medium" x-text="selectedCust.phone"></span></div>
            <div class="flex justify-between border-b pb-2"><span class="text-gray-500">Lifetime Spend:</span><span class="font-bold text-brand-700" x-text="formatCurrency(selectedCust.total_spent)"></span></div>
            <div class="flex justify-between border-b pb-2"><span class="text-gray-500">Loyalty Points:</span><span class="font-bold text-yellow-600" x-text="selectedCust.loyalty_points"></span></div>
          </div>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function customersApp() {
  return {
    customers: [], search: '', showModal: false, selectedCust: null,
    form: { first_name: '', last_name: '', phone_number: '', email: '' },

    async load() {
      if (!requireAuth()) return;
      try {
        this.customers = await apiFetch(`/customers/?search=${this.search}`);
      } catch (e) { alert(e.message); }
    },

    async createCustomer() {
      try {
        await apiFetch('/customers/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        this.form = { first_name: '', last_name: '', phone_number: '', email: '' };
        this.load();
      } catch (e) { alert(e.response?.data?.error || e.message); }
    },

    viewDetails(c) {
      this.selectedCust = c;
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created customers.html UI page")
print("\n🎉 Done! Restart the server and refresh.")