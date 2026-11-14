import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update MTNMoMoService to return exact error
# ============================================================
momo_path = BACKEND_PATH / "payments" / "momo_service.py"
m_content = momo_path.read_text(encoding="utf-8")

new_token_method = '''    def get_access_token(self):
        url = f"{self.base_url}/collection/token/"
        headers = {
            "Ocp-Apim-Subscription-Key": self.subscription_key,
            "Authorization": "Basic " + base64.b64encode(f"{self.api_user}:{self.api_key}".encode()).decode()
        }
        try:
            res = requests.post(url, headers=headers)
            res.raise_for_status()
            return {"success": True, "token": res.json().get("access_token")}
        except requests.exceptions.HTTPError as e:
            # Extract the exact error message from MTN
            error_msg = e.response.text if e.response else str(e)
            return {"success": False, "error": f"MTN API Error: {error_msg}"}
        except Exception as e:
            return {"success": False, "error": str(e)}
'''

# Replace the old get_access_token method
m_content = re.sub(r"    def get_access_token\(self\):.*?return None", new_token_method.strip(), m_content, flags=re.DOTALL)
momo_path.write_text(m_content, encoding="utf-8")
print("✅ Updated MTN service to return exact errors")

# ============================================================
# 2. Update Views (Test Connection & Delete Gateway)
# ============================================================
views_path = BACKEND_PATH / "payments" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Update test_gateway_connection to use the new token dict
v_content = v_content.replace(
    "token = service.get_access_token()\n        if token:",
    "token_result = service.get_access_token()\n        if token_result.get('success'):"
).replace(
    'return Response({"error": "Failed to authenticate. Check your Subscription Key, API User, and API Key."}, status=400)',
    'return Response({"error": token_result.get("error")}, status=400)'
)

# Add Delete View
delete_view = '''
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def delete_gateway(request):
    if request.user.user_type not in ("TENANT_OWNER", "ADMIN"):
        return Response({"error": "Insufficient permissions"}, status=403)
        
    provider = request.data.get("provider")
    config = BranchPaymentConfig.objects.filter(branch=request.branch, provider=provider).first()
    
    if config:
        config.delete()
        return Response({"success": True, "message": "Configuration deleted."})
    
    return Response({"error": "Config not found"}, status=404)
'''
if "def delete_gateway" not in v_content:
    v_content += "\n\n" + delete_view
views_path.write_text(v_content, encoding="utf-8")

# Update URLs
urls_path = BACKEND_PATH / "payments" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "delete_gateway" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("delete-gateway/", views.delete_gateway, name="delete_gateway"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Added Delete Gateway endpoint")

# ============================================================
# 3. Update Frontend Settings UI
# ============================================================
settings_path = BACKEND_PATH / "templates" / "pos" / "settings.html"
s_content = settings_path.read_text(encoding="utf-8")

# Add Delete button to the list
old_buttons = '''            <div class="flex gap-3">
              <button @click="testGateway(c.provider)" class="text-blue-600 hover:text-blue-800 text-xs font-bold" :disabled="testingGw === c.provider">
                <span x-show="testingGw !== c.provider">Test</span>
                <span x-show="testingGw === c.provider">Testing...</span>
              </button>
              <button @click="editGateway(c)" class="text-brand-600 hover:underline text-xs font-medium">Edit</button>
            </div>'''

new_buttons = '''            <div class="flex gap-3">
              <button @click="testGateway(c.provider)" class="text-blue-600 hover:text-blue-800 text-xs font-bold" :disabled="testingGw === c.provider">
                <span x-show="testingGw !== c.provider">Test</span>
                <span x-show="testingGw === c.provider">Testing...</span>
              </button>
              <button @click="editGateway(c)" class="text-brand-600 hover:underline text-xs font-medium">Edit</button>
              <button @click="deleteGateway(c.provider)" class="text-red-500 hover:text-red-700 text-xs font-medium">Delete</button>
            </div>'''
s_content = s_content.replace(old_buttons, new_buttons)

# Add deleteGateway function to JS
new_js = '''
    async deleteGateway(provider) {
      if (!confirm(`Are you sure you want to delete the ${this.formatProviderName(provider)} configuration?`)) return;
      try {
        await apiFetch('/payments/delete-gateway/', { method: 'POST', body: JSON.stringify({ provider }) });
        this.load(); // Refresh the list
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },
'''
s_content = s_content.replace("    async saveGateway() {", new_js + "\n    async saveGateway() {")

settings_path.write_text(s_content, encoding="utf-8")
print("✅ Updated Settings UI with Delete button")

print("\n🎉 Done! Restart the server.")