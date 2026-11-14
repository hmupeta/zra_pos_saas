import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def patch_file(path, old, new, is_regex=False):
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if is_regex:
        content = re.sub(old, new, content, flags=re.DOTALL)
    else:
        content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")

# ============================================================
# 1. Fix API Error Handling in api.js
# ============================================================
api_js = BACKEND_PATH / "static" / "pos" / "api.js"
js_content = api_js.read_text(encoding="utf-8")

old_parse = """
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = new Error((data && data.error) || `HTTP ${res.status}`);
    err.response = { status: res.status, data };
    throw err;
  }
  return data;
"""

new_parse = """
  const text = await res.text();
  let data = null;
  
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (e) {
      // If it's not JSON, it's likely an HTML error page (500/404)
      console.error("Non-JSON response received:", text.substring(0, 200));
      if (!res.ok) throw new Error(`Server Error (${res.status}). Check console.`);
      return text;
    }
  }

  if (!res.ok) {
    const err = new Error((data && data.error) || `HTTP ${res.status}`);
    err.response = { status: res.status, data };
    throw err;
  }
  return data;
"""
patch_file(api_js, old_parse, new_parse)
print("✅ Fixed api.js to handle non-JSON server errors gracefully")

# ============================================================
# 2. Ensure User View and URLs are correct
# ============================================================
core_views = BACKEND_PATH / "core" / "views.py"
views_content = core_views.read_text(encoding="utf-8")

# Add Company Settings view (Get/Update)
company_view = '''
from django.http import QueryDict
from core.models import Company

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def company_settings(request):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Only Admins can change settings"}, status=403)
    
    branch = request.branch
    if not branch:
        return Response({"error": "No active branch"}, status=400)

    if request.method == "GET":
        return Response({
            "name": branch.name,
            "tpin": branch.tpin,
            "address": branch.address,
            "phone": branch.phone,
            "email": branch.email,
            "logo_url": branch.logo.url if branch.logo else None,
        })

    # POST (Handle Multipart for Logo Upload)
    branch.name = request.data.get("name", branch.name)
    branch.tpin = request.data.get("tpin", branch.tpin)
    branch.address = request.data.get("address", branch.address)
    branch.phone = request.data.get("phone", branch.phone)
    branch.email = request.data.get("email", branch.email)

    if "logo" in request.FILES:
        branch.logo = request.FILES["logo"]

    branch.save()
    return Response({"success": True, "message": "Settings updated"})
'''

if "def company_settings" not in views_content:
    with open(core_views, "a", encoding="utf-8") as f:
        f.write("\n\n" + company_view.strip())

# Make sure users_list_create is exactly right
users_view_fix = '''
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def users_list_create(request):
    if request.user.user_type != "TENANT_OWNER":
        return Response({"error": "Only Tenant Admins can manage users"}, status=403)

    if request.method == "GET":
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(tenant=request.tenant).order_by("-date_joined")
        return Response([{
            "id": u.id, "username": u.username, "email": u.email,
            "user_type": u.user_type, "is_active": u.is_active,
        } for u in users])

    data = request.data
    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")
    role = data.get("user_type", "SALES_AGENT")

    if not username or not password:
        return Response({"error": "Username and password required"}, status=400)

    from django.contrib.auth import get_user_model
    from django.db import transaction
    from core.models import BranchAccess
    User = get_user_model()

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, email=email, password=password,
                tenant=request.tenant, user_type=role, employment_status="ACTIVE"
            )
            if request.branch:
                BranchAccess.objects.create(user=user, company=request.branch, is_default=True)
            return Response({"success": True, "id": user.id}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
'''

# Replace current users view
views_content = core_views.read_text(encoding="utf-8")
pattern = r"@api_view\(\[\"GET\", \"POST\"\]\)\ndef users_list_create\(request\):.*?status=500\)"
views_content = re.sub(pattern, users_view_fix.strip(), views_content, flags=re.DOTALL)
core_views.write_text(views_content, encoding="utf-8")
print("✅ Fixed users_list_create view")

core_urls = BACKEND_PATH / "core" / "urls.py"
urls_content = core_urls.read_text(encoding="utf-8")
if "company_settings" not in urls_content:
    urls_content = urls_content.replace(
        "urlpatterns = [",
        "from .views import users_list_create, company_settings\n\nurlpatterns = [\n    path('users/', users_list_create, name='users'),\n    path('company/', company_settings, name='company_settings'),"
    )
    core_urls.write_text(urls_content, encoding="utf-8")
print("✅ Updated core/urls.py")

# ============================================================
# 3. Update Receipt HTML Template for Logo & Background
# ============================================================
receipt_tpl = BACKEND_PATH / "templates" / "receipts" / "receipt.html"
new_receipt_tpl = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Receipt - {{ invoice.invoice_number }}</title>
    <style>
        @page { size: 80mm auto; margin: 5mm; }
        * { box-sizing: border-box; }
        body {
            font-family: "Courier New", monospace;
            font-size: 11px;
            margin: 0;
            padding: 0;
            width: 100%;
            position: relative;
        }
        /* Watermark Logo */
        {% if company.logo %}
        body::before {
            content: "";
            position: fixed;
            top: 30%;
            left: 50%;
            transform: translate(-50%, -50%);
            width: 60%;
            height: 60%;
            background-image: url('{{ company.logo.url }}');
            background-size: contain;
            background-repeat: no-repeat;
            background-position: center;
            opacity: 0.08; /* Adjust transparency */
            z-index: -1;
        }
        {% endif %}
        
        .center { text-align: center; }
        .logo-header { max-width: 50mm; max-height: 20mm; margin-bottom: 5px; }
        .company-name { font-size: 16px; font-weight: bold; margin-bottom: 4px; }
        .divider { border-top: 1px dashed #000; margin: 6px 0; }
        table { width: 100%; border-collapse: collapse; }
        table.items th, table.items td { text-align: left; padding: 2px 0; font-size: 10px; }
        table.items th { border-bottom: 1px solid #000; }
        .text-right { text-align: right; }
        .total-row { font-size: 14px; font-weight: bold; padding-top: 4px; }
        .zra-box { border: 1px solid #000; padding: 4px; margin: 8px 0; text-align: center; font-size: 10px; }
        .footer { margin-top: 12px; text-align: center; font-size: 10px; }
    </style>
</head>
<body>
    <div class="center">
        {% if company.logo %}
            <img src="{{ company.logo.url }}" class="logo-header" alt="Logo" />
        {% endif %}
        <div class="company-name">{{ company_name }}</div>
        {% if company %}
            <div>{{ company.address }}</div>
            <div>Tel: {{ company.phone }}</div>
            <div>TPIN: {{ company.tpin }}</div>
        {% endif %}
    </div>

    <div class="divider"></div>

    <div>
        <div><strong>Invoice:</strong> {{ invoice.invoice_number }}</div>
        <div><strong>Date:</strong> {{ invoice.created_at|date:"Y-m-d H:i" }}</div>
        {% if invoice.customer_name and invoice.customer_name != "Cash Customer" %}
        <div><strong>Customer:</strong> {{ invoice.customer_name }}</div>
        {% endif %}
    </div>

    <div class="divider"></div>

    <table class="items">
        <thead>
            <tr>
                <th>Item</th>
                <th class="text-right">Qty</th>
                <th class="text-right">Price</th>
                <th class="text-right">Total</th>
            </tr>
        </thead>
        <tbody>
            {% for item in items %}
            <tr>
                <td>{{ item.product.name }}</td>
                <td class="text-right">{{ item.quantity|floatformat:0 }}</td>
                <td class="text-right">{{ item.unit_price|floatformat:2 }}</td>
                <td class="text-right">{{ item.total|floatformat:2 }}</td>
            </tr>
            {% endfor %}
        </tbody>
    </table>

    <div class="divider"></div>

    <table>
        <tr>
            <td>Subtotal:</td>
            <td class="text-right">K{{ invoice.subtotal|floatformat:2 }}</td>
        </tr>
        <tr>
            <td>VAT (16%):</td>
            <td class="text-right">K{{ invoice.tax_total|floatformat:2 }}</td>
        </tr>
        <tr class="total-row">
            <td>TOTAL:</td>
            <td class="text-right">K{{ invoice.total|floatformat:2 }}</td>
        </tr>
    </table>

    {% if invoice.zra_validation_code %}
    <div class="zra-box">
        <div><strong>ZRA SMART INVOICE</strong></div>
        <div>Code: {{ invoice.zra_validation_code }}</div>
    </div>
    {% endif %}

    <div class="footer">
        <div>Thank you for your business!</div>
    </div>
</body>
</html>
'''
receipt_tpl.parent.mkdir(parents=True, exist_ok=True)
receipt_tpl.write_text(new_receipt_tpl.strip(), encoding="utf-8")
print("✅ Updated HTML receipt template with logo & watermark")

# ============================================================
# 4. Update Settings UI
# ============================================================
settings_html = BACKEND_PATH / "templates" / "pos" / "settings.html"
new_settings = '''
{% extends "pos/base.html" %}
{% block title %}Shop Settings{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="settingsPage()" x-init="load()">
    <h1 class="text-2xl font-bold mb-6">Shop Settings & Branding</h1>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <!-- Branding Form -->
      <div class="card p-6">
        <h2 class="font-semibold mb-4 text-lg">Company Details</h2>
        <form @submit.prevent="save()" class="space-y-4">
          <div>
            <label class="block text-sm mb-1">Shop/Branch Name</label>
            <input type="text" x-model="form.name" class="input-field" required>
          </div>
          <div>
            <label class="block text-sm mb-1">TPIN</label>
            <input type="text" x-model="form.tpin" class="input-field">
          </div>
          <div>
            <label class="block text-sm mb-1">Phone</label>
            <input type="text" x-model="form.phone" class="input-field">
          </div>
          <div>
            <label class="block text-sm mb-1">Email</label>
            <input type="email" x-model="form.email" class="input-field">
          </div>
          <div>
            <label class="block text-sm mb-1">Address (Printed on Receipt)</label>
            <textarea x-model="form.address" class="input-field" rows="2"></textarea>
          </div>
          
          <div class="border-t pt-4 mt-4">
            <label class="block text-sm font-medium mb-2">Shop Logo</label>
            <p class="text-xs text-gray-500 mb-2">Appears on receipts and as a watermark.</p>
            <input type="file" @change="handleFile" accept="image/*" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100">
          </div>

          <button type="submit" class="btn-primary w-full mt-4" :disabled="saving">
            <span x-show="!saving">Save Settings</span>
            <span x-show="saving">Saving...</span>
          </button>
        </form>
      </div>

      <!-- Logo Preview -->
      <div class="card p-6 flex flex-col items-center justify-center bg-gray-50">
        <h2 class="font-semibold mb-4 text-gray-500">Current Logo</h2>
        <template x-if="previewUrl || form.logo_url">
          <img :src="previewUrl || form.logo_url" class="max-w-xs max-h-64 object-contain bg-white p-4 shadow-sm border rounded-lg" alt="Shop Logo">
        </template>
        <template x-if="!previewUrl && !form.logo_url">
          <div class="text-gray-400 text-sm">No logo uploaded yet.</div>
        </template>
      </div>

    </div>

    <div class="card p-6 mt-6">
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
    </div>

  </div>
</div>
<script>
function settingsPage() {
  return {
    form: { name: '', tpin: '', address: '', phone: '', email: '', logo_url: null },
    configs: [],
    saving: false,
    previewUrl: null,
    logoFile: null,

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try { 
        this.form = await apiFetch('/auth/company/');
        this.configs = await apiFetch('/payments/configs/');
      } catch (e) { alert(e.message); }
    },

    handleFile(e) {
      const file = e.target.files[0];
      if (file) {
        this.logoFile = file;
        this.previewUrl = URL.createObjectURL(file);
      }
    },

    async save() {
      this.saving = true;
      try {
        const fd = new FormData();
        fd.append('name', this.form.name);
        fd.append('tpin', this.form.tpin);
        fd.append('address', this.form.address);
        fd.append('phone', this.form.phone);
        fd.append('email', this.form.email);
        if (this.logoFile) fd.append('logo', this.logoFile);

        await apiFetch('/auth/company/', {
          method: 'POST',
          body: fd,
          // Tell fetch not to set Content-Type (let browser set boundary)
          headers: { 'Authorization': `Token ${getToken()}` }
        });
        
        alert('Settings updated successfully!');
        this.logoFile = null;
        this.previewUrl = null;
        this.load();
      } catch (e) {
        alert('Failed to update settings: ' + e.message);
      } finally {
        this.saving = false;
      }
    }
  }
}
</script>
{% endblock %}
'''
settings_html.write_text(new_settings.strip(), encoding="utf-8")
print("✅ Updated Settings UI with branding form")

# ============================================================
# 5. Ensure ReceiptService.to_html passes logo properly
# ============================================================
receipt_service = BACKEND_PATH / "sales" / "receipt_service.py"
rs_content = receipt_service.read_text(encoding="utf-8")

new_to_html = '''
    def to_html(self):
        from django.template.loader import render_to_string
        return render_to_string(
            "receipts/receipt.html",
            {
                "invoice": self.invoice,
                "company": self.invoice.company,
                "company_name": self.invoice.company.name,
                "items": self.invoice.items.all(),
            }
        )
'''

pattern = r"    def to_html\(self\):.*?return render_to_string\(.*?\n        \)"
rs_content = re.sub(pattern, new_to_html.strip(), rs_content, flags=re.DOTALL)
receipt_service.write_text(rs_content, encoding="utf-8")
print("✅ Ensured ReceiptService passes company object for logo")
print("\\n🎉 Done! Restart server and refresh.")