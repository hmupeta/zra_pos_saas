import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Backend: Flexible MoMo Initiation
# ============================================================
views_path = BACKEND_PATH / "payments" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

new_initiate_view = '''
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initiate_momo_payment(request):
    phone = request.data.get("phone")
    amount = request.data.get("amount")
    provider = request.data.get("provider") # e.g. MTN_DIRECT, AIRTEL_DIRECT
    
    if not request.branch:
        return Response({"error": "No branch context. Please refresh and select a branch."}, status=400)
    if not phone or not amount or not provider:
        return Response({"error": "Phone, amount, and provider are required"}, status=400)

    config = BranchPaymentConfig.objects.filter(branch=request.branch, provider=provider).first()
    if not config:
        return Response({"error": f"{provider} is not configured for this branch."}, status=400)

    if provider == "MTN_DIRECT":
        service = MTNMoMoService(config)
        import uuid
        ext_id = str(uuid.uuid4())
        
        res = service.request_to_pay(phone, amount, ext_id, "POS Sale")
        
        if res.get("success"):
            GatewayTransaction.objects.create(
                tenant=request.tenant, branch=request.branch,
                provider="MTN_DIRECT", reference_id=res["reference_id"],
                amount=amount, phone=phone, status="PENDING"
            )
            return Response({"success": True, "reference_id": res["reference_id"]})
        else:
            return Response({"error": res.get("error")}, status=400)
            
    elif provider in ["AIRTEL_DIRECT", "ZAMTEL_DIRECT"]:
        # Placeholder for Airtel/Zamtel integration
        return Response({"error": f"{provider} API is not yet implemented. Please use Cash or MTN."}, status=400)

    return Response({"error": "Unsupported provider"}, status=400)
'''

# Replace the old initiate_momo_payment
pattern = r"@api_view\(\[\"POST\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef initiate_momo_payment\(request\):.*?return Response\(\{\"error\": \"Unsupported provider\"\}, status=400\)"
v_content = re.sub(pattern, new_initiate_view.strip(), v_content, flags=re.DOTALL)
views_path.write_text(v_content, encoding="utf-8")
print("✅ Updated backend to accept dynamic provider (MTN, Airtel, etc.)")


# ============================================================
# 2. Update Frontend: POS Dynamic Selection
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
p_content = pos_path.read_text(encoding="utf-8")

# 1. Add dynamic PG dropdown to checkout modal
old_momo_input = '''        <div x-show="paymentMethod === 'MOMO' || paymentMethod === 'CARD'" class="mb-4">
          <label class="block text-sm font-medium mb-1">Customer Phone Number</label>
          <input type="tel" x-model="paymentPhone" placeholder="e.g., 0971234567" class="input-field text-lg" required>
          <p class="text-xs text-gray-500 mt-1">A prompt will be sent to this number.</p>
        </div>'''

new_momo_input = '''        <div x-show="paymentMethod === 'MOMO' || paymentMethod === 'CARD'" class="mb-4 space-y-3">
          <div x-show="availableMomoProviders.length > 0">
            <label class="block text-sm font-medium mb-1">Select Network</label>
            <select x-model="selectedProvider" class="input-field">
              <template x-for="p in availableMomoProviders" :key="p">
                <option :value="p" x-text="formatProviderName(p)"></option>
              </template>
            </select>
          </div>
          <div x-show="availableMomoProviders.length === 0" class="text-sm text-red-600 p-2 bg-red-50 rounded">
            ⚠️ No Mobile Money gateways are configured for this branch. Please go to Settings to add one.
          </div>
          
          <div>
            <label class="block text-sm font-medium mb-1">Customer Phone Number</label>
            <input type="tel" x-model="paymentPhone" placeholder="e.g., 0971234567" class="input-field text-lg" required>
            <p class="text-xs text-gray-500 mt-1">A prompt will be sent to this number.</p>
          </div>
        </div>'''
p_content = p_content.replace(old_momo_input, new_momo_input)

# 2. Add state variables for providers
p_content = p_content.replace(
    "paymentPhone: '', pollingPayment: false,",
    "paymentPhone: '', pollingPayment: false, availableMomoProviders: [], selectedProvider: '', paymentConfigs: [],"
)

# 3. Load payment configs on init
p_content = p_content.replace(
    "this.shift = await apiFetch('/sales/current-shift/')",
    "this.paymentConfigs = await apiFetch('/payments/configs/');\n        this.availableMomoProviders = this.paymentConfigs.map(c => c.provider);\n        if (this.availableMomoProviders.length > 0) { this.selectedProvider = this.availableMomoProviders[0]; }\n        this.shift = await apiFetch('/sales/current-shift/')"
)

# 4. Add formatProviderName helper
p_content = p_content.replace(
    "    async doCheckout() {",
    '''    formatProviderName(p) {
      const names = { 'MTN_DIRECT': 'MTN Mobile Money', 'AIRTEL_DIRECT': 'Airtel Money', 'ZAMTEL_DIRECT': 'Zamtel Kwacha' };
      return names[p] || p;
    },

    async doCheckout() {'''
)

# 5. Update doCheckout to pass the selected provider
p_content = p_content.replace(
    "phone: this.paymentPhone,\n              amount: this.cart.totals.total",
    "phone: this.paymentPhone,\n              amount: this.cart.totals.total,\n              provider: this.selectedProvider"
)

# 6. Add better error logging to the catch block in doCheckout
p_content = p_content.replace(
    "alert(e.response?.data?.error || e.message);\n      } finally {\n        this.busy = false;\n      }\n    },",
    "alert('Payment Error: ' + (e.response?.data?.error || e.message));\n      } finally {\n        this.busy = false;\n      }\n    },"
)

pos_path.write_text(p_content, encoding="utf-8")
print("✅ Updated POS UI with dynamic Network Selection dropdown")

print("\n🎉 Done! Restart the server.")