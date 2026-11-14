import os
import subprocess
import platform
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Models (Add all providers)
# ============================================================
models_path = BACKEND_PATH / "payments" / "models.py"
content = models_path.read_text(encoding="utf-8")

# Expand provider choices
new_providers = '''    PROVIDERS = [
        ("MTN_DIRECT", "MTN Mobile Money"),
        ("AIRTEL_DIRECT", "Airtel Money"),
        ("ZAMTEL_DIRECT", "Zamtel Kwacha"),
        ("STRIPE", "Stripe (Card)"),
        ("PAYPAL", "PayPal"),
        ("MONEYUNIFY", "MoneyUnify (Aggregated)"),
    ]'''
content = re.sub(r"    PROVIDERS = \[.*?\]", new_providers, content, flags=re.DOTALL)
models_path.write_text(content, encoding="utf-8")
print("✅ Expanded Payment Gateway providers")

# ============================================================
# 2. Backend View for MTN API User Creation
# ============================================================
views_path = BACKEND_PATH / "payments" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

mtn_user_view = '''
import requests
import uuid

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def generate_mtn_api_user(request):
    """Generates an MTN API User and API Key using a Subscription Key."""
    sub_key = request.data.get("subscription_key")
    env = request.data.get("target_env", "sandbox")
    
    if not sub_key:
        return Response({"error": "Subscription Key is required"}, status=400)

    base_url = "https://sandbox.momodeveloper.mtn.com" if env == "sandbox" else "https://proxy.momoapi.mtn.com"
    reference_id = str(uuid.uuid4())
    
    headers = {
        "Ocp-Apim-Subscription-Key": sub_key,
        "X-Reference-Id": reference_id,
        "Content-Type": "application/json"
    }
    
    try:
        # 1. Create API User
        res_user = requests.post(f"{base_url}/v1_0/apiuser", headers=headers, json={"providerCallbackHost": "https://webhook.site"})
        
        if res_user.status_code not in (200, 201):
            return Response({"error": f"Failed to create API User: {res_user.text}"}, status=400)
            
        # 2. Create API Key
        res_key = requests.post(f"{base_url}/v1_0/apiuser/{reference_id}/apikey", headers={"Ocp-Apim-Subscription-Key": sub_key})
        
        if res_key.status_code not in (200, 201):
            return Response({"error": f"Failed to create API Key: {res_key.text}"}, status=400)
            
        api_key = res_key.json().get("apiKey")
        
        return Response({
            "success": True,
            "api_user": reference_id,
            "api_key": api_key
        })
        
    except requests.RequestException as e:
        return Response({"error": str(e)}, status=500)
'''

if "def generate_mtn_api_user" not in v_content:
    views_path.write_text(v_content + "\n\n" + mtn_user_view, encoding="utf-8")

# Update URLs
urls_path = BACKEND_PATH / "payments" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "generate_mtn_api_user" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("mtn/generate-user/", views.generate_mtn_api_user, name="generate_mtn_api_user"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Added MTN API User Generation endpoint")

# ============================================================
# 3. Update Frontend Settings UI
# ============================================================
settings_path = BACKEND_PATH / "templates" / "pos" / "settings.html"
s_content = settings_path.read_text(encoding="utf-8")

# Replace the entire Gateway Modal
old_modal = '''    <!-- Gateway Modal -->
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

new_modal = '''    <!-- Gateway Modal -->
    <div x-show="showGatewayModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-md w-full p-6 max-h-[90vh] overflow-y-auto">
        <div class="flex justify-between items-center mb-1">
          <h2 class="text-xl font-bold">Payment Gateway Config</h2>
        </div>
        <p class="text-xs text-brand-600 font-medium mb-4">Configuring for Branch: <span x-text="form.name" class="font-bold"></span></p>
        
        <form @submit.prevent="saveGateway()" class="space-y-4">
          <div>
            <label class="block text-sm mb-1">Provider</label>
            <select x-model="gatewayForm.provider" class="input-field">
              <option value="MTN_DIRECT">MTN Mobile Money</option>
              <option value="AIRTEL_DIRECT">Airtel Money</option>
              <option value="ZAMTEL_DIRECT">Zamtel Kwacha</option>
              <option value="STRIPE">Stripe (Card)</option>
              <option value="PAYPAL">PayPal</option>
              <option value="MONEYUNIFY">MoneyUnify (Aggregated)</option>
            </select>
          </div>
          
          <!-- MTN Specific Form -->
          <template x-if="gatewayForm.provider === 'MTN_DIRECT'">
            <div class="space-y-3 border p-4 rounded-lg bg-gray-50 border-gray-200">
              <div class="flex justify-between items-center">
                <p class="text-sm font-bold text-slate-700">MTN MoMo Credentials</p>
                <select x-model="gatewayForm.mtn_target_env" class="border rounded px-2 py-1 text-xs">
                  <option value="sandbox">Sandbox</option>
                  <option value="production">Production</option>
                </select>
              </div>
              
              <div>
                <label class="text-xs text-gray-500">Subscription Key (Primary)</label>
                <input placeholder="Enter Subscription Key" x-model="gatewayForm.mtn_subscription_key" class="input-field" required>
              </div>

              <button type="button" @click="generateMtnUser()" class="w-full py-2 bg-yellow-100 text-yellow-800 text-sm font-bold rounded border border-yellow-300 hover:bg-yellow-200 transition" :disabled="generatingUser">
                <span x-text="generatingUser ? 'Generating...' : '⚡ Generate API User & Key'"></span>
              </button>

              <div>
                <label class="text-xs text-gray-500">API User</label>
                <input placeholder="Auto-generated" x-model="gatewayForm.mtn_api_user" class="input-field bg-gray-100" readonly required>
              </div>
              <div>
                <label class="text-xs text-gray-500">API Key</label>
                <input placeholder="Auto-generated" x-model="gatewayForm.mtn_api_key" class="input-field bg-gray-100" readonly required>
              </div>
            </div>
          </template>
          
          <!-- Card / PayPal / Other Forms -->
          <template x-if="['STRIPE', 'PAYPAL', 'MONEYUNIFY'].includes(gatewayForm.provider)">
            <div class="space-y-3 border p-4 rounded-lg bg-gray-50 border-gray-200">
              <p class="text-sm font-bold text-slate-700" x-text="gatewayForm.provider + ' Credentials'"></p>
              <div>
                <label class="text-xs text-gray-500">Merchant ID / Client ID</label>
                <input placeholder="Merchant ID" x-model="gatewayForm.merchant_id" class="input-field" required>
              </div>
              <div>
                <label class="text-xs text-gray-500">Secret Key / API Key</label>
                <input placeholder="Secret Key" x-model="gatewayForm.api_key" class="input-field" required>
              </div>
            </div>
          </template>

          <!-- Airtel / Zamtel Forms -->
          <template x-if="['AIRTEL_DIRECT', 'ZAMTEL_DIRECT'].includes(gatewayForm.provider)">
            <div class="space-y-3 border p-4 rounded-lg bg-gray-50 border-gray-200">
              <p class="text-sm font-bold text-slate-700" x-text="gatewayForm.provider.replace('_DIRECT', '') + ' Credentials'"></p>
              <div>
                <label class="text-xs text-gray-500">Merchant Code / Client ID</label>
                <input placeholder="Merchant Code" x-model="gatewayForm.merchant_id" class="input-field" required>
              </div>
              <div>
                <label class="text-xs text-gray-500">Client Secret / API Key</label>
                <input placeholder="API Key" x-model="gatewayForm.api_key" class="input-field" required>
              </div>
            </div>
          </template>
          
          <div class="flex gap-2 mt-6">
            <button type="button" @click="showGatewayModal = false" class="btn-secondary flex-1">Cancel</button>
            <button type="submit" class="btn-primary flex-1" :disabled="savingGw">Save to Branch</button>
          </div>
        </form>
      </div>
    </div>'''

s_content = s_content.replace(old_modal, new_modal)

# Update JS to include generation function
s_content = s_content.replace(
    "savingGw: false,",
    "savingGw: false,\n    generatingUser: false,"
)

new_js_func = '''
    async generateMtnUser() {
      if (!this.gatewayForm.mtn_subscription_key) {
        alert('Please enter the Subscription Key first.');
        return;
      }
      this.generatingUser = true;
      try {
        const res = await apiFetch('/payments/mtn/generate-user/', {
          method: 'POST',
          body: JSON.stringify({
            subscription_key: this.gatewayForm.mtn_subscription_key,
            target_env: this.gatewayForm.mtn_target_env
          })
        });
        this.gatewayForm.mtn_api_user = res.api_user;
        this.gatewayForm.mtn_api_key = res.api_key;
        alert('API User and Key generated successfully! You can now save.');
      } catch(e) {
        alert('Generation failed: ' + (e.response?.data?.error || e.message));
      } finally {
        this.generatingUser = false;
      }
    },
'''
s_content = s_content.replace("    async saveGateway() {", new_js_func + "\n    async saveGateway() {")

settings_path.write_text(s_content, encoding="utf-8")
print("✅ Rebuilt Settings UI with expanded Providers and MTN API Generation")