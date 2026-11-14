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
# 1. Update Payments Model (Track gateway transactions)
# ============================================================
models_path = BACKEND_PATH / "payments" / "models.py"
m_content = models_path.read_text(encoding="utf-8")

if "class GatewayTransaction" not in m_content:
    m_content += '''

class GatewayTransaction(models.Model):
    STATUS = [
        ("PENDING", "Pending USSD Approval"),
        ("SUCCESS", "Successful"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    branch = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    provider = models.CharField(max_length=50) # MTN_DIRECT, STRIPE, etc.
    reference_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.provider} - {self.reference_id}"
'''
    models_path.write_text(m_content, encoding="utf-8")
print("✅ Added GatewayTransaction model")

# ============================================================
# 2. Update Payments Views (Initiate & Poll)
# ============================================================
views_path = BACKEND_PATH / "payments" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

payment_views = '''
from .models import GatewayTransaction
from .momo_service import MTNMoMoService

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def initiate_momo_payment(request):
    phone = request.data.get("phone")
    amount = request.data.get("amount")
    
    if not phone or not amount:
        return Response({"error": "Phone and amount required"}, status=400)

    config = BranchPaymentConfig.objects.filter(branch=request.branch, provider="MTN_DIRECT").first()
    if not config:
        return Response({"error": "MTN is not configured for this branch"}, status=400)

    service = MTNMoMoService(config)
    import uuid
    ext_id = str(uuid.uuid4())
    
    # Trigger RequestToPay
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

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def check_payment_status(request, reference_id):
    try:
        txn = GatewayTransaction.objects.get(reference_id=reference_id)
    except GatewayTransaction.DoesNotExist:
        return Response({"error": "Transaction not found"}, status=404)

    if txn.status != "PENDING":
        return Response({"status": txn.status})

    config = BranchPaymentConfig.objects.filter(branch=request.branch, provider="MTN_DIRECT").first()
    service = MTNMoMoService(config)
    res = service.check_status(reference_id)
    
    # MTN returns status "SUCCESSFUL" or "FAILED"
    mt_status = res.get("status")
    if mt_status == "SUCCESSFUL":
        txn.status = "SUCCESS"
        txn.save()
    elif mt_status == "FAILED":
        txn.status = "FAILED"
        txn.save()
        
    return Response({"status": txn.status, "mtn_raw": res})
'''

if "def initiate_momo_payment" not in v_content:
    views_path.write_text(v_content + "\n\n" + payment_views, encoding="utf-8")
else:
    # Replace the old stub
    pattern = r"@api_view\(\[\"POST\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef initiate_momo_payment\(request\):.*?return Response\(\{\"error\": result.get\(\"error\"\)\}, status=500\)"
    v_content = re.sub(pattern, payment_views.strip(), v_content, flags=re.DOTALL)
    views_path.write_text(v_content, encoding="utf-8")

# Update URLs
urls_path = BACKEND_PATH / "payments" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "check_payment_status" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path("momo/initiate/", views.initiate_momo_payment, name="initiate_momo_payment"),
    path("momo/status/<str:reference_id>/", views.check_payment_status, name="check_payment_status"),'''
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Added Payment Initiation & Polling endpoints")

# ============================================================
# 3. Update Cart Checkout to verify payment
# ============================================================
cart_service = BACKEND_PATH / "sales" / "cart_service.py"
c_content = cart_service.read_text(encoding="utf-8")

# Modify checkout signature and add validation
old_checkout = '''    @staticmethod
    @transaction.atomic
    def checkout(tenant_id, branch_id, shift, cashier, payment_method="CASH"):
        cart = CartService.get(tenant_id, branch_id, shift.id)
        if not cart["items"]:
            raise ValueError("Cart is empty")'''

new_checkout = '''    @staticmethod
    @transaction.atomic
    def checkout(tenant_id, branch_id, shift, cashier, payment_method="CASH", payment_reference=None):
        cart = CartService.get(tenant_id, branch_id, shift.id)
        if not cart["items"]:
            raise ValueError("Cart is empty")
            
        # Validate gateway payment
        if payment_method in ("MOMO", "CARD"):
            from payments.models import GatewayTransaction
            if not payment_reference:
                raise ValueError("Payment reference is required for mobile/card payments")
                
            txn = GatewayTransaction.objects.filter(reference_id=payment_reference, status="SUCCESS").first()
            if not txn:
                raise ValueError("Payment has not been confirmed by the gateway yet")
                
            cart_total = Decimal(str(CartService.totals(cart)["total"]))
            if txn.amount != cart_total:
                raise ValueError(f"Payment amount ({txn.amount}) does not match cart total ({cart_total})")'''
            
c_content = c_content.replace(old_checkout, new_checkout)
cart_service.write_text(c_content, encoding="utf-8")
print("✅ Updated Cart Checkout to require Gateway Payment validation")

# ============================================================
# 4. Update Sales View to pass payment_reference
# ============================================================
sales_views = BACKEND_PATH / "sales" / "views.py"
s_content = sales_views.read_text(encoding="utf-8")
s_content = s_content.replace(
    "invoice = CartService.checkout(\n            request.tenant.id, request.branch.id, shift, request.user,\n            request.data.get(\"payment_method\", \"CASH\"),\n        )",
    "invoice = CartService.checkout(\n            request.tenant.id, request.branch.id, shift, request.user,\n            request.data.get(\"payment_method\", \"CASH\"),\n            request.data.get(\"payment_reference\")\n        )"
)
sales_views.write_text(s_content, encoding="utf-8")
print("✅ Updated Sales View to pass reference")

# ============================================================
# 5. Frontend POS Updates
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
p_content = pos_path.read_text(encoding="utf-8")

# Add Phone Number input to the Checkout modal
old_pay_btn = '''        <button
              disabled={busy}
              onClick={doCheckout}
              className="btn-primary w-full py-3 text-base"
            >
              {busy ? 'Processing...' : `Pay ${formatCurrency(cart.totals.total)}`}
        </button>'''

# We need to replace the Alpine.js version of this
old_pay_btn_alpine = '''        <button @click="doCheckout()" :disabled="busy" class="btn-primary w-full py-3 text-base">
          <span x-show="!busy">Pay <span x-text="formatCurrency(cart.totals.total || 0)"></span></span>
          <span x-show="busy">Processing...</span>
        </button>'''

new_pay_btn_alpine = '''        <div x-show="paymentMethod === 'MOMO' || paymentMethod === 'CARD'" class="mb-4">
          <label class="block text-sm font-medium mb-1">Customer Phone Number</label>
          <input type="tel" x-model="paymentPhone" placeholder="e.g., 0971234567" class="input-field text-lg" required>
          <p class="text-xs text-gray-500 mt-1">A prompt will be sent to this number.</p>
        </div>

        <button @click="doCheckout()" :disabled="busy || ((paymentMethod === 'MOMO' || paymentMethod === 'CARD') && !paymentPhone)" class="btn-primary w-full py-3 text-base">
          <span x-show="!busy">Pay <span x-text="formatCurrency(cart.totals.total || 0)"></span></span>
          <span x-show="busy">Processing...</span>
        </button>'''
p_content = p_content.replace(old_pay_btn_alpine, new_pay_btn_alpine)

# Add Polling Modal
polling_modal = '''
    <!-- Polling Modal -->
    <div x-show="pollingPayment" x-cloak class="fixed inset-0 bg-black/80 flex items-center justify-center z-[60] p-4">
      <div class="bg-white rounded-xl max-w-sm w-full p-8 text-center shadow-2xl">
        <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-brand-600 mx-auto mb-6"></div>
        <h2 class="text-xl font-bold text-slate-900 mb-2">Waiting for Payment</h2>
        <p class="text-gray-500 mb-6">A USSD prompt has been sent to <strong x-text="paymentPhone"></strong>. Please enter your PIN to authorize.</p>
        <button @click="pollingPayment = false; busy = false" class="text-red-600 text-sm hover:underline">Cancel Transaction</button>
      </div>
    </div>
'''
p_content = p_content.replace("<!-- Receipt Modal -->", polling_modal + "\n    <!-- Receipt Modal -->")

# Add JS variables and logic
p_content = p_content.replace(
    "checkoutOpen: false, receiptModal: null,",
    "checkoutOpen: false, receiptModal: null, paymentPhone: '', pollingPayment: false,"
)

new_do_checkout = '''
    async doCheckout() {
      if (this.paymentMethod === 'CREDIT' && !this.customerId) {
        alert('Please select a registered customer to use Store Credit.'); return;
      }
      
      this.busy = true;
      let payment_reference = null;

      try {
        // 1. If Mobile Money, initiate the RequestToPay
        if (this.paymentMethod === 'MOMO') {
          const initRes = await apiFetch('/payments/momo/initiate/', {
            method: 'POST',
            body: JSON.stringify({
              phone: this.paymentPhone,
              amount: this.cart.totals.total
            })
          });
          
          payment_reference = initRes.reference_id;
          this.pollingPayment = true;
          
          // 2. Poll for status
          let isPaid = false;
          for (let i = 0; i < 30; i++) { // Timeout after 60s
            await new Promise(r => setTimeout(r, 2000));
            
            const statusRes = await apiFetch(`/payments/momo/status/${payment_reference}/`);
            if (statusRes.status === 'SUCCESS') { isPaid = true; break; }
            if (statusRes.status === 'FAILED') { throw new Error('Payment was declined or cancelled.'); }
          }
          
          this.pollingPayment = false;
          if (!isPaid) throw new Error('Payment timed out. Please try again.');
        }

        // 3. Complete the Sale (Backend will verify the reference)
        const res = await apiFetch('/sales/cart/checkout/', {
          method: 'POST',
          body: JSON.stringify({ 
            payment_method: this.paymentMethod,
            payment_reference: payment_reference
          }),
        });
        
        const receipt = await apiFetch(`/sales/invoices/${res.invoice_id}/receipt.txt`);
        this.receiptModal = { ...res, text: receipt.text };
        this.cart = { items: [], totals: {} };
        this.customerName = ''; this.customerId = null; this.discountAmount = 0;
        this.paymentPhone = '';
        this.checkoutOpen = false;
        this.paymentMethod = 'CASH';
        
      } catch (e) {
        this.pollingPayment = false;
        alert(e.response?.data?.error || e.message);
      } finally {
        this.busy = false;
      }
    },
'''
# Regex replace doCheckout
p_content = re.sub(r"    async doCheckout\(\) \{.*?this.busy = false;\n      \}\n    \},", new_do_checkout.strip(), p_content, flags=re.DOTALL)
pos_path.write_text(p_content, encoding="utf-8")
print("✅ Updated POS UI with Payment Polling")

# ============================================================
# 6. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "payments"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")