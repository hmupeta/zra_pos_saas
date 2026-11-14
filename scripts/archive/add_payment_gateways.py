import os
import re
import subprocess
import platform
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
# 1. Update Models (Platform SaaS Config & Tenant Branch Config)
# ============================================================
# A. Platform SaaS Config
saas_models = BACKEND_PATH / "saas" / "models.py"
s_content = saas_models.read_text(encoding="utf-8")
if "class PlatformGatewayConfig" not in s_content:
    s_content += '''

class PlatformGatewayConfig(models.Model):
    PROVIDERS = [("MTN", "MTN MoMo"), ("STRIPE", "Stripe"), ("PAYPAL", "PayPal")]
    provider = models.CharField(max_length=20, choices=PROVIDERS, unique=True)
    is_enabled = models.BooleanField(default=False)
    
    # MTN Fields
    mtn_subscription_key = models.CharField(max_length=200, blank=True)
    mtn_api_user = models.CharField(max_length=200, blank=True)
    mtn_api_key = models.CharField(max_length=200, blank=True)
    mtn_target_env = models.CharField(max_length=50, default="sandbox")
    
    # Stripe/PayPal Fields
    api_key = models.CharField(max_length=200, blank=True)
    secret_key = models.CharField(max_length=200, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SaaS Config: {self.provider}"
'''
    saas_models.write_text(s_content, encoding="utf-8")

# B. Tenant Branch Config
pay_models = BACKEND_PATH / "payments" / "models.py"
p_content = pay_models.read_text(encoding="utf-8")
if "mtn_api_user" not in p_content:
    p_content = p_content.replace(
        "extra_config = models.JSONField(default=dict, blank=True)",
        "extra_config = models.JSONField(default=dict, blank=True)\n    mtn_subscription_key = models.CharField(max_length=200, blank=True)\n    mtn_api_user = models.CharField(max_length=200, blank=True)\n    mtn_api_key = models.CharField(max_length=200, blank=True)\n    mtn_target_env = models.CharField(max_length=50, default='sandbox')"
    )
    pay_models.write_text(p_content, encoding="utf-8")
print("✅ Updated Database Models")

# ============================================================
# 2. MTN MoMo Integration Service
# ============================================================
momo_service = BACKEND_PATH / "payments" / "momo_service.py"
momo_code = '''
import requests
import uuid
import base64
from django.conf import settings

class MTNMoMoService:
    """Handles MTN MoMo API interactions."""
    
    def __init__(self, config):
        self.config = config
        self.base_url = "https://sandbox.momodeveloper.mtn.com" if config.mtn_target_env == "sandbox" else "https://proxy.momoapi.mtn.com"
        self.subscription_key = config.mtn_subscription_key
        self.api_user = config.mtn_api_user
        self.api_key = config.mtn_api_key
        self.target_env = config.mtn_target_env

    def get_access_token(self):
        url = f"{self.base_url}/collection/token/"
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Authorization": "Basic " + base64.b64encode(f"{self.api_user}:{self.api_key}".encode()).decode()
        }
        try:
            res = requests.post(url, headers=headers)
            res.raise_for_status()
            return res.json().get("access_token")
        except Exception as e:
            print(f"MTN Token Error: {e}")
            return None

    def request_to_pay(self, phone, amount, external_id, payer_message="Payment"):
        token = self.get_access_token()
        if not token: return {"error": "Could not authenticate with MTN"}

        reference_id = str(uuid.uuid4())
        url = f"{self.base_url}/collection/v1_0/requesttopay"
        
        # Format phone to standard MTN format (e.g., 260971234567)
        phone_clean = str(phone).replace("+", "").replace(" ", "")
        if phone_clean.startswith("0"):
            phone_clean = "260" + phone_clean[1:]

        headers = {
            "Authorization": f"Bearer {token}",
            "X-Reference-Id": reference_id,
            "X-Target-Environment": self.target_env,
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Content-Type": "application/json"
        }
        payload = {
            "amount": str(amount),
            "currency": "ZMW",
            "externalId": external_id,
            "payer": {
                "partyIdType": "MSISDN",
                "partyId": phone_clean
            },
            "payerMessage": payer_message,
            "payeeNote": payer_message
        }
        
        try:
            res = requests.post(url, headers=headers, json=payload)
            if res.status_code in (200, 202):
                return {"success": True, "reference_id": reference_id}
            else:
                return {"error": res.text}
        except Exception as e:
            return {"error": str(e)}

    def check_status(self, reference_id):
        token = self.get_access_token()
        if not token: return {"error": "Auth failed"}
        
        url = f"{self.base_url}/collection/v1_0/requesttopay/{reference_id}"
        headers = {
            "Authorization": f"Bearer {token}",
            "X-Target-Environment": self.target_env,
            "Ocp-Apim-Subscription-Key": self.subscription_key
        }
        try:
            res = requests.get(url, headers=headers)
            return res.json()
        except Exception as e:
            return {"error": str(e)}
'''
momo_service.write_text(momo_code.strip(), encoding="utf-8")
print("✅ Created MTN MoMo API Service")

# ============================================================
# 3. Backend Views (Platform Admin & Tenant Wallet)
# ============================================================
# A. Platform Admin Gateway Views
saas_views = BACKEND_PATH / "saas" / "views.py"
s_views_content = saas_views.read_text(encoding="utf-8")
platform_gateways_view = '''
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def platform_gateways(request):
    from .models import PlatformGatewayConfig
    
    if request.method == "GET":
        configs = PlatformGatewayConfig.objects.all()
        return Response([{
            "provider": c.provider, "is_enabled": c.is_enabled,
            "mtn_subscription_key": c.mtn_subscription_key,
            "mtn_api_user": c.mtn_api_user, "mtn_api_key": c.mtn_api_key,
            "mtn_target_env": c.mtn_target_env,
            "api_key": c.api_key, "secret_key": c.secret_key
        } for c in configs])

    data = request.data
    config, _ = PlatformGatewayConfig.objects.get_or_create(provider=data["provider"])
    config.is_enabled = data.get("is_enabled", False)
    
    if data["provider"] == "MTN":
        config.mtn_subscription_key = data.get("mtn_subscription_key", "")
        config.mtn_api_user = data.get("mtn_api_user", "")
        config.mtn_api_key = data.get("mtn_api_key", "")
        config.mtn_target_env = data.get("mtn_target_env", "sandbox")
    else:
        config.api_key = data.get("api_key", "")
        config.secret_key = data.get("secret_key", "")
        
    config.save()
    return Response({"success": True})
'''
if "def platform_gateways" not in s_views_content:
    saas_views.write_text(s_views_content + "\n\n" + platform_gateways_view, encoding="utf-8")

# Update URLs
saas_urls = BACKEND_PATH / "saas" / "urls.py"
s_urls_content = saas_urls.read_text(encoding="utf-8")
if "platform_gateways" not in s_urls_content:
    s_urls_content = s_urls_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("admin/gateways/", views.platform_gateways, name="platform_gateways"),'
    )
    saas_urls.write_text(s_urls_content, encoding="utf-8")

# B. Tenant Wallet Aggregation View
pay_views = BACKEND_PATH / "payments" / "views.py"
p_views_content = pay_views.read_text(encoding="utf-8")
wallet_view = '''
from django.db.models import Sum
from sales.models import Invoice
from core.models import Company

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def tenant_wallets(request):
    """Aggregate all payments across all branches for this tenant."""
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    branches = Company.objects.filter(tenant=request.tenant, is_active=True)
    
    branch_stats = []
    total_cash = 0
    total_momo = 0
    total_card = 0

    for b in branches:
        invoices = Invoice.objects.filter(company=b, status="PAID")
        
        cash = sum(inv.total for inv in invoices if inv.payment_method == "CASH") or 0
        momo = sum(inv.total for inv in invoices if inv.payment_method in ("MOMO", "MTN", "AIRTEL", "ZAMTEL")) or 0
        card = sum(inv.total for inv in invoices if inv.payment_method == "CARD") or 0
        
        total_cash += cash
        total_momo += momo
        total_card += card
        
        branch_stats.append({
            "id": b.id, "name": b.name,
            "cash": float(cash), "momo": float(momo), "card": float(card),
            "total": float(cash + momo + card)
        })

    return Response({
        "summary": {
            "total_cash": float(total_cash),
            "total_momo": float(total_momo),
            "total_card": float(total_card),
            "grand_total": float(total_cash + total_momo + total_card)
        },
        "branches": branch_stats
    })
'''
if "def tenant_wallets" not in p_views_content:
    pay_views.write_text(p_views_content + "\n\n" + wallet_view, encoding="utf-8")

# Update URLs
pay_urls = BACKEND_PATH / "payments" / "urls.py"
p_urls_content = pay_urls.read_text(encoding="utf-8")
if "tenant_wallets" not in p_urls_content:
    p_urls_content = p_urls_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("wallets/", views.tenant_wallets, name="tenant_wallets"),'
    )
    pay_urls.write_text(p_urls_content, encoding="utf-8")
print("✅ Added API endpoints for Platform Gateways and Tenant Wallets")

# ============================================================
# 4. Frontend Routes
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
w_content = views_web.read_text(encoding="utf-8")
if "def platform_gateways_page" not in w_content:
    w_content += "\n\ndef platform_gateways_page(request):\n    return render(request, 'pos/platform_gateways.html')\n\ndef tenant_wallets_page(request):\n    return render(request, 'pos/wallets.html')\n"
    views_web.write_text(w_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
wu_content = urls_web.read_text(encoding="utf-8")
if "/platform/gateways" not in wu_content:
    wu_content = wu_content.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('platform/gateways', views_web.platform_gateways_page, name='platform_gateways_page'),\n    path('wallets', views_web.tenant_wallets_page, name='tenant_wallets_page'),"
    )
    urls_web.write_text(wu_content, encoding="utf-8")

# Add Wallets to Tenant Nav
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
n_content = nav_path.read_text(encoding="utf-8")
if "href=\"/wallets\"" not in n_content:
    n_content = n_content.replace(
        '<a href="/shifts" class="nav-link"',
        '<a href="/wallets" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)"><i data-lucide="wallet" class="w-4 h-4 mr-3"></i> Wallets</a>\n    <a href="/shifts" class="nav-link"'
    )
    nav_path.write_text(n_content, encoding="utf-8")

# Add Gateway Config to Platform Nav
for tpl in ["platform_dashboard.html", "platform_tenants.html", "platform_applications.html", "platform_billing.html"]:
    p = BACKEND_PATH / "templates" / "pos" / tpl
    if p.exists():
        c = p.read_text(encoding="utf-8")
        if "/platform/gateways" not in c:
            c = c.replace(
                '<a href="/platform/billing" class="nav-link',
                '<a href="/platform/gateways" class="nav-link"><i data-lucide="settings" class="w-4 h-4 mr-3"></i> Gateways</a>\n      <a href="/platform/billing" class="nav-link'
            )
            p.write_text(c, encoding="utf-8")
print("✅ Added UI Routes to Sidebars")

# ============================================================
# 5. Create the UI Templates
# ============================================================
# A. Platform Admin Gateways UI
gateways_html = '''
{% extends "pos/base.html" %}
{% block title %}Gateway Config{% endblock %}
{% block body %}
<div class="h-screen flex bg-slate-50">
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
      <a href="/platform/billing" class="nav-link"><i data-lucide="credit-card" class="w-4 h-4 mr-3"></i> Billing</a>
      <a href="/platform/gateways" class="nav-link active"><i data-lucide="settings" class="w-4 h-4 mr-3"></i> Gateways</a>
    </nav>
  </aside>

  <div class="flex-1 overflow-y-auto p-8" x-data="gatewaysApp()" x-init="load()">
    <h1 class="text-2xl font-bold mb-6">SaaS Payment Gateways</h1>
    <p class="text-gray-500 mb-8">Configure how your platform collects subscription money from tenants.</p>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- MTN MoMo -->
      <div class="card p-6 border-t-4 border-yellow-400">
        <div class="flex justify-between items-center mb-4">
          <h2 class="font-bold text-lg flex items-center gap-2"><i data-lucide="smartphone" class="text-yellow-600"></i> MTN MoMo</h2>
          <input type="checkbox" x-model="configs.MTN.is_enabled" class="w-5 h-5">
        </div>
        <form @submit.prevent="save('MTN')" class="space-y-3">
          <input placeholder="Subscription Key" x-model="configs.MTN.mtn_subscription_key" class="input-field">
          <input placeholder="API User" x-model="configs.MTN.mtn_api_user" class="input-field">
          <input placeholder="API Key" x-model="configs.MTN.mtn_api_key" class="input-field">
          <select x-model="configs.MTN.mtn_target_env" class="input-field">
            <option value="sandbox">Sandbox</option>
            <option value="production">Production</option>
          </select>
          <button type="submit" class="btn-primary w-full">Save MTN Config</button>
        </form>
      </div>

      <!-- Stripe -->
      <div class="card p-6 border-t-4 border-indigo-500">
        <div class="flex justify-between items-center mb-4">
          <h2 class="font-bold text-lg flex items-center gap-2"><i data-lucide="credit-card" class="text-indigo-600"></i> Stripe / Card</h2>
          <input type="checkbox" x-model="configs.STRIPE.is_enabled" class="w-5 h-5">
        </div>
        <form @submit.prevent="save('STRIPE')" class="space-y-3">
          <input placeholder="Publishable Key" x-model="configs.STRIPE.api_key" class="input-field">
          <input placeholder="Secret Key" x-model="configs.STRIPE.secret_key" class="input-field">
          <button type="submit" class="btn-primary w-full">Save Stripe Config</button>
        </form>
      </div>
    </div>
  </div>
</div>
<script>
function gatewaysApp() {
  return {
    configs: {
      MTN: { provider: 'MTN', is_enabled: false, mtn_subscription_key: '', mtn_api_user: '', mtn_api_key: '', mtn_target_env: 'sandbox' },
      STRIPE: { provider: 'STRIPE', is_enabled: false, api_key: '', secret_key: '' }
    },
    async load() {
      try {
        const res = await apiFetch('/saas/admin/gateways/');
        res.forEach(c => { if (this.configs[c.provider]) this.configs[c.provider] = c; });
      } catch(e) { alert(e.message); }
    },
    async save(provider) {
      try {
        await apiFetch('/saas/admin/gateways/', { method: 'POST', body: JSON.stringify(this.configs[provider]) });
        alert('Configuration saved!');
        this.load();
      } catch(e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''
(Path(BACKEND_PATH) / "templates" / "pos" / "platform_gateways.html").write_text(gateways_html.strip(), encoding="utf-8")

# B. Tenant Wallets UI
wallets_html = '''
{% extends "pos/base.html" %}
{% block title %}Consolidated Wallets{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="walletApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Consolidated Wallets</h1>
        <p class="text-gray-500 text-sm mt-1">Track cash and mobile money across all your branches.</p>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8" x-show="data">
      <div class="card p-5 border-l-4 border-green-500 bg-gradient-to-br from-green-50 to-white">
        <div class="text-sm font-medium text-gray-500 mb-1">Total Cash Collected</div>
        <div class="text-2xl font-bold text-slate-900" x-text="formatCurrency(data?.summary.total_cash)"></div>
      </div>
      <div class="card p-5 border-l-4 border-yellow-400 bg-gradient-to-br from-yellow-50 to-white">
        <div class="text-sm font-medium text-gray-500 mb-1">Total MoMo Collected</div>
        <div class="text-2xl font-bold text-slate-900" x-text="formatCurrency(data?.summary.total_momo)"></div>
      </div>
      <div class="card p-5 border-l-4 border-indigo-500 bg-gradient-to-br from-indigo-50 to-white">
        <div class="text-sm font-medium text-gray-500 mb-1">Total Card Collected</div>
        <div class="text-2xl font-bold text-slate-900" x-text="formatCurrency(data?.summary.total_card)"></div>
      </div>
      <div class="card p-5 bg-slate-900 text-white">
        <div class="text-sm font-medium text-slate-300 mb-1">Grand Total (All Time)</div>
        <div class="text-2xl font-bold" x-text="formatCurrency(data?.summary.grand_total)"></div>
      </div>
    </div>

    <div class="card overflow-hidden" x-show="data">
      <div class="p-4 border-b bg-gray-50">
        <h2 class="font-bold text-slate-700">Revenue by Branch</h2>
      </div>
      <table class="w-full text-sm">
        <thead class="bg-gray-100 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-6 py-3">Branch Name</th>
            <th class="px-6 py-3 text-right">Cash</th>
            <th class="px-6 py-3 text-right">MoMo</th>
            <th class="px-6 py-3 text-right">Card</th>
            <th class="px-6 py-3 text-right font-bold">Total</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="b in data?.branches" :key="b.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-6 py-4 font-bold text-slate-800" x-text="b.name"></td>
              <td class="px-6 py-4 text-right text-gray-600" x-text="formatCurrency(b.cash)"></td>
              <td class="px-6 py-4 text-right text-gray-600" x-text="formatCurrency(b.momo)"></td>
              <td class="px-6 py-4 text-right text-gray-600" x-text="formatCurrency(b.card)"></td>
              <td class="px-6 py-4 text-right font-bold text-brand-700" x-text="formatCurrency(b.total)"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

  </div>
</div>
<script>
function walletApp() {
  return {
    data: null,
    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try { this.data = await apiFetch('/payments/wallets/'); } catch(e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''
(Path(BACKEND_PATH) / "templates" / "pos" / "wallets.html").write_text(wallets_html.strip(), encoding="utf-8")
print("✅ Created Platform Gateways and Wallets UI")

# ============================================================
# 6. Update Tenant Settings UI for MTN MoMo
# ============================================================
settings_path = BACKEND_PATH / "templates" / "pos" / "settings.html"
s_html = settings_path.read_text(encoding="utf-8")

# Add MTN fields to the Branch Payment Config modal
old_fields = '''          <select x-model="form.provider" class="input-field">
            <option value="MONEYUNIFY">MoneyUnify</option>
            <option value="MTN_DIRECT">MTN Direct</option>
            <option value="AIRTEL_DIRECT">Airtel Direct</option>
          </select>
          <input placeholder="Merchant ID" x-model="form.merchant_id" class="input-field" required>
          <input placeholder="API Key" x-model="form.api_key" class="input-field">'''

new_fields = '''          <select x-model="form.provider" class="input-field">
            <option value="MTN_DIRECT">MTN Mobile Money</option>
            <option value="MONEYUNIFY">MoneyUnify (Other)</option>
          </select>
          
          <template x-if="form.provider === 'MTN_DIRECT'">
            <div class="space-y-2 border p-3 rounded bg-gray-50">
              <p class="text-xs text-gray-500 font-medium mb-2">MTN MoMo Credentials</p>
              <input placeholder="Subscription Key" x-model="form.mtn_subscription_key" class="input-field" required>
              <input placeholder="API User" x-model="form.mtn_api_user" class="input-field" required>
              <input placeholder="API Key" x-model="form.mtn_api_key" class="input-field" required>
              <select x-model="form.mtn_target_env" class="input-field">
                <option value="sandbox">Sandbox</option>
                <option value="production">Production</option>
              </select>
            </div>
          </template>
          
          <template x-if="form.provider !== 'MTN_DIRECT'">
            <div class="space-y-2">
              <input placeholder="Merchant ID" x-model="form.merchant_id" class="input-field" required>
              <input placeholder="API Key" x-model="form.api_key" class="input-field">
            </div>
          </template>'''

s_html = s_html.replace(old_fields, new_fields)

# Update the JS save function to include the new fields
s_html = s_html.replace(
    "form: { provider: 'MONEYUNIFY', merchant_id: '', api_key: '', is_default: true },",
    "form: { provider: 'MTN_DIRECT', merchant_id: '', api_key: '', is_default: true, mtn_subscription_key: '', mtn_api_user: '', mtn_api_key: '', mtn_target_env: 'sandbox' },"
)
settings_path.write_text(s_html, encoding="utf-8")
print("✅ Updated Tenant Settings for MTN Direct Credentials")

# ============================================================
# 7. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "saas", "payments"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")