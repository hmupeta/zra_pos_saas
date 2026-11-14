import os
import subprocess
import platform
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Backend: Add Branch Management APIs
# ============================================================
core_views = BACKEND_PATH / "core" / "views.py"
content = core_views.read_text(encoding="utf-8")

branch_api = '''
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def branches_manage(request):
    if request.user.user_type not in ("TENANT_OWNER", "ADMIN"):
        return Response({"error": "Only Tenant Admins can manage branches"}, status=403)

    if request.method == "GET":
        from core.models import Company
        branches = Company.objects.filter(tenant=request.tenant)
        return Response([{
            "id": b.id, "name": b.name, "tpin": b.tpin, "phone": b.phone,
            "address": b.address, "is_active": b.is_active
        } for b in branches])

    # POST: Create new branch
    data = request.data
    from core.models import Company
    from django.utils.text import slugify
    
    # Check plan limits
    if not request.tenant.within_plan_limits("branches"):
         return Response({"error": f"Branch limit reached for your plan"}, status=403)

    b = Company.objects.create(
        tenant=request.tenant, name=data["name"],
        branch_code=data.get("branch_code", f"00{Company.objects.filter(tenant=request.tenant).count() + 1}"),
        tpin=data.get("tpin", ""), phone=data.get("phone", ""), address=data.get("address", "")
    )
    # Automatically assign the creator to the new branch
    from core.models import BranchAccess
    BranchAccess.objects.create(user=request.user, company=b)
    
    return Response({"success": True, "id": b.id})
'''
if "def branches_manage" not in content:
    core_views.write_text(content + "\n\n" + branch_api, encoding="utf-8")

# Update URLs
core_urls = BACKEND_PATH / "core" / "urls.py"
u_content = core_urls.read_text(encoding="utf-8")
if "branches_manage" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("branches/manage/", views.branches_manage, name="branches_manage"),'
    )
    core_urls.write_text(u_content, encoding="utf-8")
print("✅ Added Branch Management API")

# ============================================================
# 2. Frontend: Route & Nav for Branches
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
w_content = views_web.read_text(encoding="utf-8")
if "def branches_page" not in w_content:
    w_content += "\n\ndef branches_page(request):\n    return render(request, 'pos/branches.html')\n"
    views_web.write_text(w_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
wu_content = urls_web.read_text(encoding="utf-8")
if "/branches" not in wu_content:
    wu_content = wu_content.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('branches', views_web.branches_page, name='branches_page'),"
    )
    urls_web.write_text(wu_content, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
n_content = nav_path.read_text(encoding="utf-8")
if "href=\"/branches\"" not in n_content:
    n_content = n_content.replace(
        '<a href="/wallets" class="nav-link"',
        '<a href="/branches" class="nav-link" x-show="getUser()?.user_type === \'TENANT_OWNER\'"><i data-lucide="building" class="w-4 h-4 mr-3"></i> Branches</a>\n    <a href="/wallets" class="nav-link"'
    )
    nav_path.write_text(n_content, encoding="utf-8")
print("✅ Added Branches to Sidebar")

# ============================================================
# 3. Rebuild Settings UI (Add Gateway Config Button)
# ============================================================
settings_path = BACKEND_PATH / "templates" / "pos" / "settings.html"
s_content = settings_path.read_text(encoding="utf-8")

# Replace the entire Payment Gateways section
old_gateway_section = '''    <div class="card p-6 mt-6">
      <h2 class="font-semibold mb-4">Payment Gateways (this branch)</h2>
      <div class="space-y-2">
        <template x-for="c in configs" :key="c.id">
          <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
            <div>
              <div class="font-medium" x-text="c.provider"></div>
              <div class="text-xs text-gray-500">Merchant: <span x-text="c.merchant_id || '-'"></span></div>
            </div>
          </div>
        </template>
        <div x-show="configs.length === 0" class="text-sm text-gray-400">No payment gateways configured.</div>
      </div>
    </div>'''

new_gateway_section = '''    <div class="card p-6 mt-6">
      <div class="flex justify-between items-center mb-4">
        <div>
          <h2 class="font-semibold text-lg">Payment Gateways</h2>
          <p class="text-xs text-gray-500">Configure how this specific branch collects money.</p>
        </div>
        <button @click="showGatewayModal = true" class="btn-primary text-sm">+ Add Config</button>
      </div>
      
      <div class="space-y-2">
        <template x-for="c in configs" :key="c.id">
          <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div>
              <div class="font-bold text-slate-800" x-text="c.provider"></div>
              <div class="text-xs text-gray-500">Merchant: <span x-text="c.merchant_id || '-'"></span></div>
            </div>
            <button @click="editGateway(c)" class="text-brand-600 hover:underline text-xs font-medium">Edit</button>
          </div>
        </template>
        <div x-show="configs.length === 0" class="text-sm text-gray-400 italic">No payment gateways configured for this branch.</div>
      </div>
    </div>

    <!-- Gateway Modal -->
    <div x-show="showGatewayModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-md w-full p-6">
        <h2 class="text-xl font-bold mb-4">Payment Gateway Config</h2>
        <form @submit.prevent="saveGateway()" class="space-y-3">
          <select x-model="gatewayForm.provider" class="input-field">
            <option value="MTN_DIRECT">MTN Mobile Money</option>
            <option value="MONEYUNIFY">MoneyUnify</option>
          </select>
          
          <template x-if="gatewayForm.provider === 'MTN_DIRECT'">
            <div class="space-y-2 border p-3 rounded bg-gray-50">
              <p class="text-xs text-gray-500 font-medium mb-2">MTN MoMo Credentials</p>
              <input placeholder="Subscription Key" x-model="gatewayForm.mtn_subscription_key" class="input-field" required>
              <input placeholder="API User" x-model="gatewayForm.mtn_api_user" class="input-field" required>
              <input placeholder="API Key" x-model="gatewayForm.mtn_api_key" class="input-field" required>
              <select x-model="gatewayForm.mtn_target_env" class="input-field">
                <option value="sandbox">Sandbox</option>
                <option value="production">Production</option>
              </select>
            </div>
          </template>
          
          <template x-if="gatewayForm.provider !== 'MTN_DIRECT'">
            <div class="space-y-2">
              <input placeholder="Merchant ID" x-model="gatewayForm.merchant_id" class="input-field" required>
              <input placeholder="API Key" x-model="gatewayForm.api_key" class="input-field">
            </div>
          </template>
          
          <div class="flex gap-2 mt-4">
            <button type="button" @click="showGatewayModal = false" class="btn-secondary flex-1">Cancel</button>
            <button type="submit" class="btn-primary flex-1" :disabled="savingGw">Save</button>
          </div>
        </form>
      </div>
    </div>'''

s_content = s_content.replace(old_gateway_section, new_gateway_section)

# Update JS in Settings
s_content = s_content.replace(
    "saving: false,\n    previewUrl: null,\n    logoFile: null,",
    "saving: false,\n    previewUrl: null,\n    logoFile: null,\n    showGatewayModal: false,\n    savingGw: false,\n    gatewayForm: { provider: 'MTN_DIRECT', merchant_id: '', api_key: '', mtn_subscription_key: '', mtn_api_user: '', mtn_api_key: '', mtn_target_env: 'sandbox' },"
)

new_js = '''
    editGateway(c) {
      this.gatewayForm = { ...c };
      this.showGatewayModal = true;
    },

    async saveGateway() {
      this.savingGw = true;
      try {
        await apiFetch('/payments/configs/', { method: 'POST', body: JSON.stringify(this.gatewayForm) });
        this.showGatewayModal = false;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.savingGw = false; }
    },
'''
s_content = s_content.replace("    async save() {", new_js + "\n    async save() {")

settings_path.write_text(s_content, encoding="utf-8")
print("✅ Updated Settings UI with Gateway Add/Edit Modal")

# ============================================================
# 4. Create Branches UI
# ============================================================
branches_html = '''
{% extends "pos/base.html" %}
{% block title %}Branches{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="branchesApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Branch Management</h1>
        <p class="text-gray-500 text-sm mt-1">Manage all your store locations.</p>
      </div>
      <button @click="showModal = true; resetForm()" class="btn-primary">+ Add Branch</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Branch Name</th>
            <th class="px-4 py-3">TPIN</th>
            <th class="px-4 py-3">Phone</th>
            <th class="px-4 py-3 text-center">Status</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="b in branches" :key="b.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-bold text-slate-800" x-text="b.name"></td>
              <td class="px-4 py-3 font-mono text-xs" x-text="b.tpin"></td>
              <td class="px-4 py-3 text-gray-500" x-text="b.phone"></td>
              <td class="px-4 py-3 text-center">
                <span class="px-2 py-0.5 rounded text-xs" :class="b.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'" x-text="b.is_active ? 'Active' : 'Inactive'"></span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Add Branch Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4">Add New Branch</h2>
          <form @submit.prevent="create()" class="space-y-3">
            <input placeholder="Branch Name (e.g. Lusaka Mall)" x-model="form.name" class="input-field" required>
            <input placeholder="ZRA TPIN" x-model="form.tpin" class="input-field" required>
            <input placeholder="Phone Number" x-model="form.phone" class="input-field">
            <textarea placeholder="Physical Address" x-model="form.address" class="input-field" rows="2"></textarea>
            
            <div class="flex gap-2 mt-4">
              <button type="button" @click="showModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1" :disabled="saving">Save Branch</button>
            </div>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function branchesApp() {
  return {
    branches: [], showModal: false, saving: false,
    form: { name: '', tpin: '', phone: '', address: '' },

    async load() {
      if (!requireAuth()) return;
      try { this.branches = await apiFetch('/auth/branches/manage/'); } catch(e) { alert(e.message); }
    },

    resetForm() {
      this.form = { name: '', tpin: '', phone: '', address: '' };
    },

    async create() {
      this.saving = true;
      try {
        await apiFetch('/auth/branches/manage/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    }
  }
}
</script>
{% endblock %}
'''
(Path(BACKEND_PATH) / "templates" / "pos" / "branches.html").write_text(branches_html.strip(), encoding="utf-8")
print("✅ Created branches.html UI")

print("\n🎉 Done! Restart the server.")