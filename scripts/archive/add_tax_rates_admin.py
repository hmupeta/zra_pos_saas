import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Backend View to handle POST/PUT
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Replace the simple GET endpoint with a full CRUD endpoint
new_tax_view = '''
@api_view(["GET", "POST", "PUT"])
@permission_classes([IsAuthenticated])
def tax_rates_list(request):
    if request.method == "GET":
        taxes = TaxRate.objects.filter(tenant=request.tenant)
        return Response([{
            "id": t.id, "name": t.name, "rate": float(t.rate), 
            "zra_tax_code": t.zra_tax_code, "tax_type": t.tax_type, "is_active": t.is_active
        } for t in taxes])
        
    # Only Managers/Owners can modify tax rates
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    if request.method == "POST":
        t = TaxRate.objects.create(
            tenant=request.tenant, name=data["name"], rate=data["rate"],
            zra_tax_code=data["zra_tax_code"], tax_type=data["tax_type"]
        )
        return Response({"success": True, "id": t.id}, status=201)
        
    elif request.method == "PUT":
        try:
            t = TaxRate.objects.get(id=data["id"], tenant=request.tenant)
            t.name = data.get("name", t.name)
            t.rate = data.get("rate", t.rate)
            t.zra_tax_code = data.get("zra_tax_code", t.zra_tax_code)
            t.tax_type = data.get("tax_type", t.tax_type)
            t.is_active = data.get("is_active", t.is_active)
            t.save()
            return Response({"success": True})
        except TaxRate.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
'''

import re
v_content = re.sub(r"@api_view\(\[\"GET\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef tax_rates_list\(request\):.*?return Response\(\[.*?\]\)", new_tax_view.strip(), v_content, flags=re.DOTALL)
views_path.write_text(v_content, encoding="utf-8")
print("✅ Updated tax_rates_list view to support CRUD")

# ============================================================
# 2. Add Route & Navigation
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")
if "def tax_rates_page" not in web_content:
    web_content += "\n\ndef tax_rates_page(request):\n    return render(request, 'pos/tax_rates.html')\n"
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/tax-rates" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('tax-rates', views_web.tax_rates_page, name='tax_rates_page'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")

# Add link to sidebar under Products
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")
if "href=\"/tax-rates\"" not in nav_content:
    nav_content = nav_content.replace(
        '<a href="/products" class="nav-link"',
        '<a href="/tax-rates" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)">Tax Rates</a>\n    <a href="/products" class="nav-link"'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Tax Rates to Sidebar")

# ============================================================
# 3. Create Tax Rates UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "tax_rates.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Tax Rates{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="taxApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Tax Rates & Bands</h1>
      <button @click="showModal = true; resetForm()" class="btn-primary">+ Add Tax Rate</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Tax Name</th>
            <th class="px-4 py-3">Rate (%)</th>
            <th class="px-4 py-3">ZRA Code</th>
            <th class="px-4 py-3">Type</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="t in taxes" :key="t.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-medium" x-text="t.name"></td>
              <td class="px-4 py-3 font-bold" x-text="t.rate + '%'"></td>
              <td class="px-4 py-3 font-mono text-xs" x-text="t.zra_tax_code"></td>
              <td class="px-4 py-3"><span class="bg-blue-100 text-blue-800 px-2 py-0.5 rounded text-xs" x-text="t.tax_type"></span></td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded text-xs" :class="t.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'" x-text="t.is_active ? 'Active' : 'Inactive'"></span>
              </td>
              <td class="px-4 py-3 text-right">
                <button @click="editTax(t)" class="text-brand-600 hover:underline text-xs">Edit</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Add/Edit Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4" x-text="form.id ? 'Edit Tax Rate' : 'New Tax Rate'"></h2>
          <form @submit.prevent="save()" class="space-y-4">
            
            <div>
              <label class="block text-sm mb-1">Tax Name</label>
              <input type="text" x-model="form.name" placeholder="e.g. VAT 16%" class="input-field" required>
            </div>
            
            <div class="grid grid-cols-2 gap-4">
              <div>
                <label class="block text-sm mb-1">Rate (%)</label>
                <input type="number" step="0.01" x-model="form.rate" class="input-field" required>
              </div>
              <div>
                <label class="block text-sm mb-1">ZRA Tax Code</label>
                <input type="text" x-model="form.zra_tax_code" placeholder="e.g. A or C" class="input-field" required>
              </div>
            </div>

            <div>
              <label class="block text-sm mb-1">Tax Type</label>
              <select x-model="form.tax_type" class="input-field">
                <option value="STANDARD">Standard (VAT)</option>
                <option value="ZERO">Zero Rated</option>
                <option value="EXEMPT">Exempt</option>
              </select>
            </div>

            <div x-show="form.id">
              <label class="flex items-center gap-2 text-sm">
                <input type="checkbox" x-model="form.is_active"> Active
              </label>
            </div>

            <div class="flex gap-2 mt-4">
              <button type="button" @click="showModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1">Save</button>
            </div>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function taxApp() {
  return {
    taxes: [], showModal: false,
    form: { id: null, name: '', rate: 0, zra_tax_code: '', tax_type: 'STANDARD', is_active: true },

    async load() {
      if (!requireAuth()) return;
      try { this.taxes = await apiFetch('/inventory/tax-rates/'); } catch(e) { alert(e.message); }
    },

    resetForm() {
      this.form = { id: null, name: '', rate: 0, zra_tax_code: '', tax_type: 'STANDARD', is_active: true };
    },

    editTax(t) {
      this.form = { ...t };
      this.showModal = true;
    },

    async save() {
      try {
        const method = this.form.id ? 'PUT' : 'POST';
        await apiFetch('/inventory/tax-rates/', { method: method, body: JSON.stringify(this.form) });
        this.showModal = false;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created Tax Rates UI")

print("\n🎉 Done! Restart the server.")