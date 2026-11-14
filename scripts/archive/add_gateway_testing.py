import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Backend: Add Test Connection View
# ============================================================
views_path = BACKEND_PATH / "payments" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

test_view = '''
from .models import BranchPaymentConfig
from .momo_service import MTNMoMoService

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def test_gateway_connection(request):
    provider = request.data.get("provider")
    config = BranchPaymentConfig.resolve_for_branch(request.branch, provider)
    
    if not config:
        return Response({"error": "Configuration not found for this branch"}, status=404)

    if provider == "MTN_DIRECT":
        service = MTNMoMoService(config)
        token = service.get_access_token()
        if token:
            return Response({"success": True, "message": "Successfully authenticated with MTN MoMo!"})
        else:
            return Response({"error": "Failed to authenticate. Check your Subscription Key, API User, and API Key."}, status=400)
            
    elif provider == "STRIPE":
        import requests
        if not config.api_key:
            return Response({"error": "Stripe API Key is missing"}, status=400)
        # Ping Stripe balance endpoint to verify the secret key
        headers = {"Authorization": f"Bearer {config.api_key}"}
        res = requests.get("https://api.stripe.com/v1/balance", headers=headers)
        if res.status_code == 200:
            return Response({"success": True, "message": "Successfully connected to Stripe!"})
        return Response({"error": "Stripe authentication failed. Check your Secret Key."}, status=400)

    # For Airtel, Zamtel, PayPal, MoneyUnify - mock test for now
    return Response({"success": True, "message": f"Basic config check passed for {provider}."})
'''

if "def test_gateway_connection" not in v_content:
    views_path.write_text(v_content + "\n\n" + test_view, encoding="utf-8")

# Update URLs
urls_path = BACKEND_PATH / "payments" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "test_gateway_connection" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("test-connection/", views.test_gateway_connection, name="test_gateway_connection"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Added Test Connection API")

# ============================================================
# 2. Frontend: Update Settings UI
# ============================================================
settings_path = BACKEND_PATH / "templates" / "pos" / "settings.html"
s_content = settings_path.read_text(encoding="utf-8")

# Replace the gateway list rendering to add the Test button and prettier names
old_list = '''        <template x-for="c in configs" :key="c.id">
          <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div>
              <div class="font-bold text-slate-800" x-text="c.provider"></div>
              <div class="text-xs text-gray-500">Merchant: <span x-text="c.merchant_id || '-'"></span></div>
            </div>
            <button @click="editGateway(c)" class="text-brand-600 hover:underline text-xs font-medium">Edit</button>
          </div>
        </template>'''

new_list = '''        <template x-for="c in configs" :key="c.id">
          <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-100">
            <div>
              <div class="font-bold text-slate-800" x-text="formatProviderName(c.provider)"></div>
              <div class="text-xs text-gray-500">
                <template x-if="c.provider === 'MTN_DIRECT'">
                   <span>API User: <span x-text="c.mtn_api_user ? c.mtn_api_user.substring(0,8) + '...' : '-'"></span></span>
                </template>
                <template x-if="c.provider !== 'MTN_DIRECT'">
                   <span>Merchant: <span x-text="c.merchant_id || '-'"></span></span>
                </template>
              </div>
            </div>
            <div class="flex gap-3">
              <button @click="testGateway(c.provider)" class="text-blue-600 hover:text-blue-800 text-xs font-bold" :disabled="testingGw === c.provider">
                <span x-show="testingGw !== c.provider">Test</span>
                <span x-show="testingGw === c.provider">Testing...</span>
              </button>
              <button @click="editGateway(c)" class="text-brand-600 hover:underline text-xs font-medium">Edit</button>
            </div>
          </div>
        </template>'''
s_content = s_content.replace(old_list, new_list)

# Add testingGw state
s_content = s_content.replace(
    "generatingUser: false,",
    "generatingUser: false,\n    testingGw: null,"
)

# Add testGateway function and formatProviderName
new_js = '''
    formatProviderName(p) {
      const names = {
        'MTN_DIRECT': 'MTN Mobile Money',
        'AIRTEL_DIRECT': 'Airtel Money',
        'ZAMTEL_DIRECT': 'Zamtel Kwacha',
        'STRIPE': 'Stripe (Card)',
        'PAYPAL': 'PayPal',
        'MONEYUNIFY': 'MoneyUnify'
      };
      return names[p] || p;
    },

    async testGateway(provider) {
      this.testingGw = provider;
      try {
        const res = await apiFetch('/payments/test-connection/', {
          method: 'POST',
          body: JSON.stringify({ provider })
        });
        alert('✅ ' + res.message);
      } catch(e) {
        alert('❌ ' + (e.response?.data?.error || e.message));
      } finally {
        this.testingGw = null;
      }
    },
'''
s_content = s_content.replace("    async saveGateway() {", new_js + "\n    async saveGateway() {")

settings_path.write_text(s_content, encoding="utf-8")
print("✅ Updated Settings UI with Test Button")

print("\n🎉 Done! Restart the server.")