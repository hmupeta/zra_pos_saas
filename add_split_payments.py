import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Backend: Update CartService to handle multiple payments
# ============================================================
cart_service = BACKEND_PATH / "sales" / "cart_service.py"
c_content = cart_service.read_text(encoding="utf-8")

# Replace the entire checkout function
new_checkout = '''
    @staticmethod
    @transaction.atomic
    def checkout(tenant_id, branch_id, shift, cashier, payments_data):
        """
        payments_data is a list of dicts: [{'method': 'CASH', 'amount': 50}, {'method': 'MTN', 'amount': 50}]
        """
        cart = CartService.get(tenant_id, branch_id, shift.id)
        if not cart["items"]:
            raise ValueError("Cart is empty")

        totals = CartService.totals(cart)
        grand_total = Decimal(str(totals["total"]))
        
        # 1. Validate Payments
        total_paid = sum(Decimal(str(p["amount"])) for p in payments_data)
        if total_paid < grand_total:
            raise ValueError(f"Insufficient payment. Total is {grand_total}, but only {total_paid} was provided.")
        if total_paid > grand_total:
            raise ValueError("Payment amount exceeds the cart total.")

        import datetime
        inv_num = f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        
        # Determine main payment method (for the invoice record)
        methods = [p["method"] for p in payments_data]
        main_method = methods[0] if len(methods) == 1 else "SPLIT"

        customer_id = cart.get("customer_id")
        if not customer_id or customer_id == "":
            customer_id = None

        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_phone=cart.get("customer_phone", ""),
            customer_id=customer_id,
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            discount_total=totals.get("discount_amount", 0),
            total=totals["total"], status="PAID", payment_method=main_method,
        )

        # 2. Create Payment Transactions (for audit trail)
        from payments.models import PaymentTransaction
        for p in payments_data:
            PaymentTransaction.objects.create(
                invoice=invoice, payment_method=p["method"],
                amount=Decimal(str(p["amount"])), status="SUCCESS"
            )

        # 3. Create Invoice Items & Update Stock
        for item in cart["items"]:
            prod = Product.objects.select_for_update().get(pk=item["product_id"])
            InvoiceItem.objects.create(
                invoice=invoice, product=prod,
                quantity=item["quantity"], unit_price=item["price_gross"],
                tax_rate=item["tax_rate"], tax_amount=item["tax_amount"],
                total=item["line_total"], zra_item_code=item["zra_item_code"],
            )
            prod.current_stock -= Decimal(str(item["quantity"]))
            prod.save(update_fields=["current_stock"])
            BarcodeService.invalidate(tenant_id, branch_id, prod.barcode)

        # 4. Update Customer Stats
        if customer_id:
            from customers.models import Customer
            customer = Customer.objects.select_for_update().get(pk=customer_id)
            customer.total_spent += invoice.total
            points_earned = int(invoice.total / 10)
            customer.loyalty_points += points_earned
            customer.save()

        # 5. Post Accounting (Debit Cash/Bank, Credit Sales/VAT)
        from accounting.models import Account, Journal, JournalLine
        sales_acct = Account.objects.filter(tenant_id=tenant_id, code="4000").first()
        vat_acct = Account.objects.filter(tenant_id=tenant_id, code="2100").first()
        
        if sales_acct and vat_acct:
            journal = Journal.objects.create(
                tenant_id=tenant_id, company_id=branch_id, journal_number=f"JV-{inv_num}",
                date=datetime.date.today(), description=f"Sale {inv_num}", journal_type="SALES",
                status="POSTED", source_invoice=invoice, created_by=cashier
            )
            
            # Debit the respective accounts based on payment method
            for p in payments_data:
                if p["method"] == "CASH":
                    debit_acct = Account.objects.filter(tenant_id=tenant_id, code="1000").first()
                elif p["method"] in ("MOMO", "MTN", "AIRTEL", "ZAMTEL"):
                    debit_acct = Account.objects.filter(tenant_id=tenant_id, code="1010").first() # Assuming Bank
                else:
                    debit_acct = Account.objects.filter(tenant_id=tenant_id, code="1000").first() # Fallback
                
                if debit_acct:
                    JournalLine.objects.create(journal=journal, account=debit_acct, debit=Decimal(str(p["amount"])), description=f"{p['method']} Payment")

            JournalLine.objects.create(journal=journal, account=sales_acct, credit=invoice.subtotal)
            if invoice.tax_total > 0:
                JournalLine.objects.create(journal=journal, account=vat_acct, credit=invoice.tax_total)

        CartService.clear(tenant_id, branch_id, shift.id)
        return invoice
'''

# Replace the existing checkout method
pattern = r"    @staticmethod\n    @transaction\.atomic\n    def checkout\(tenant_id, branch_id, shift, cashier, payment_method=\"CASH\", payment_reference=None\):.*?return invoice"
if re.search(pattern, c_content, flags=re.DOTALL):
    c_content = re.sub(pattern, new_checkout.strip(), c_content, flags=re.DOTALL)
    cart_service.write_text(c_content, encoding="utf-8")
    print("✅ Rebuilt CartService to handle split payments and correct accounting.")
else:
    print("⚠️ Could not find the exact checkout function.")

# ============================================================
# 2. Backend: Update Sales View to pass payments array
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

old_checkout_view = '''        invoice = CartService.checkout(
            request.tenant.id, request.branch.id, shift, request.user,
            request.data.get("payment_method", "CASH"),
            request.data.get("payment_reference")
        )'''

new_checkout_view = '''        # Accept array of payments from the frontend
        payments = request.data.get("payments", [])
        if not payments:
            return Response({"error": "No payment details provided"}, status=400)

        invoice = CartService.checkout(
            request.tenant.id, request.branch.id, shift, request.user,
            payments
        )'''

if old_checkout_view in v_content:
    v_content = v_content.replace(old_checkout_view, new_checkout_view)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Updated Sales View to accept multi-payment data.")
else:
    print("⚠️ Could not find checkout view to patch.")

# ============================================================
# 3. Update the Accounting Signal for Split Payments
# ============================================================
signal_path = BACKEND_PATH / "accounting" / "signals.py"
if signal_path.exists():
    # We already moved to manual journal creation in the CartService for split payments.
    # So we disable the auto-signal for Invoice to prevent double-posting.
    s_content = signal_path.read_text(encoding="utf-8")
    s_content = s_content.replace(
        "@receiver(post_save, sender=Invoice)",
        "# @receiver(post_save, sender=Invoice)  # Disabled: Handled manually in CartService for split payments"
    )
    signal_path.write_text(s_content, encoding="utf-8")
    print("✅ Disabled duplicate accounting signal.")

# ============================================================
# 4. Frontend: Rebuild Checkout Modal in pos.html
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
p_content = pos_path.read_text(encoding="utf-8")

# Replace the Checkout Modal HTML block
old_modal = '''  <!-- Checkout Modal -->
  <div x-show="checkoutOpen" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-xl max-w-md w-full p-6 max-h-[90vh] overflow-y-auto">
      <div class="flex justify-between items-center mb-4">
        <h2 class="text-xl font-bold">Checkout</h2>
        <button @click="checkoutOpen = false"><i data-lucide="x" class="w-5 h-5 text-gray-400"></i></button>
      </div>
      
      <div class="text-center py-4 mb-4 bg-gray-50 rounded-lg">
        <div class="text-sm text-gray-500">Total to pay</div>
        <div class="text-3xl font-bold text-brand-700 mt-1" x-text="formatCurrency(cart.totals.total || 0)"></div>
      </div>

      <div class="space-y-2 mb-4">
        <template x-for="m in ['CASH','MOMO','CARD']" :key="m">
          <button @click="paymentMethod = m"
                  :class="paymentMethod === m ? 'border-brand-500 bg-brand-50' : 'border-gray-200'"
                  class="w-full flex items-center gap-3 px-4 py-3 rounded-lg border-2 transition">
            <span x-text="m === 'CASH' ? '💵 Cash' : m === 'MOMO' ? '📱 Mobile Money' : '💳 Card'"></span>
          </button>
        </template>
      </div>

      <!-- MoMo Dropdown -->
      <div x-show="paymentMethod === 'MOMO'">
        <div x-show="availableMomoProviders.length > 0" class="mb-4">
          <label class="block text-sm font-medium mb-1">Select Network</label>
          <select x-model="selectedProvider" class="input-field bg-white">
            <template x-for="p in availableMomoProviders" :key="p">
              <option :value="p" x-text="formatProviderName(p)"></option>
            </template>
          </select>
        </div>
        <div class="mb-4">
          <label class="block text-sm font-medium mb-1">Customer Phone Number</label>
          <input type="tel" x-model="paymentPhone" placeholder="e.g., 0971234567" class="input-field text-lg" required>
          <p class="text-xs text-gray-500 mt-1">A USSD prompt will be sent to this number.</p>
        </div>
      </div>

      <button @click="doCheckout()" :disabled="busy || (paymentMethod === 'MOMO' && !paymentPhone)" class="btn-primary w-full py-3 text-base mt-2">
        <span x-show="!busy">Pay <span x-text="formatCurrency(cart.totals.total || 0)"></span></span>
        <span x-show="busy">Processing...</span>
      </button>
    </div>
  </div>'''

new_modal = '''  <!-- Checkout Modal (Split Payments) -->
  <div x-show="checkoutOpen" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-xl max-w-lg w-full p-6 max-h-[90vh] overflow-y-auto">
      <div class="flex justify-between items-center mb-4 border-b pb-2">
        <h2 class="text-xl font-bold">Complete Payment</h2>
        <button @click="checkoutOpen = false"><i data-lucide="x" class="w-5 h-5 text-gray-400"></i></button>
      </div>
      
      <div class="flex justify-between items-center py-4 bg-gray-50 rounded-lg px-4 mb-4 border">
        <div class="text-sm font-bold text-gray-600 uppercase">Grand Total</div>
        <div class="text-3xl font-extrabold text-brand-700" x-text="formatCurrency(cart.totals.total || 0)"></div>
      </div>

      <!-- Payment Lines -->
      <div class="space-y-3 mb-4">
        <template x-for="(payment, idx) in payments" :key="idx">
          <div class="flex gap-2 items-center bg-white border p-2 rounded-lg shadow-sm">
            <select x-model="payment.method" class="input-field w-32">
              <option value="CASH">Cash</option>
              <option value="MOMO">Mobile Money</option>
              <option value="CARD">Card</option>
            </select>
            
            <input type="number" step="0.01" x-model.number="payment.amount" class="input-field flex-1 text-right font-bold" placeholder="0.00">
            
            <button @click="payments.splice(idx, 1)" x-show="payments.length > 1" class="text-red-500 hover:text-red-700 p-1">
              <i data-lucide="trash-2" class="w-4 h-4"></i>
            </button>
          </div>
        </template>
      </div>

      <button @click="payments.push({method: 'CASH', amount: remainingToPay})" class="text-sm text-brand-600 font-bold hover:underline mb-4 flex items-center gap-1">
        + Add Payment Method
      </button>

      <!-- Amount Remaining -->
      <div class="flex justify-between text-lg font-bold border-t pt-3 mb-4">
        <span>Remaining:</span>
        <span :class="remainingToPay > 0 ? 'text-red-600' : 'text-green-600'" x-text="formatCurrency(remainingToPay)"></span>
      </div>

      <button @click="doCheckout()" :disabled="busy || remainingToPay !== 0" class="btn-primary w-full py-3 text-base">
        <span x-show="!busy">Complete Sale</span>
        <span x-show="busy">Processing...</span>
      </button>
      <p x-show="remainingToPay < 0" class="text-center text-red-500 text-xs mt-2">Payment exceeds total. Please adjust.</p>
    </div>
  </div>'''

if old_modal in p_content:
    p_content = p_content.replace(old_modal, new_modal)
    print("✅ Replaced Checkout Modal with Split Payment UI.")
else:
    print("⚠️ Could not find exact modal block. Checking for variations.")
    # Fallback to regex if needed
    pattern = r"<!-- Checkout Modal -->.*?</div>\s*</div>"
    p_content = re.sub(pattern, new_modal, p_content, flags=re.DOTALL)
    print("✅ Replaced Checkout Modal using regex.")

# ============================================================
# 5. Update POS JavaScript logic
# ============================================================
# Add payment state variables
old_state = "paymentMethod: 'CASH', paymentPhone: '', pollingPayment: false,"
new_state = "payments: [{ method: 'CASH', amount: 0 }], paymentPhone: '', pollingPayment: false,"
p_content = p_content.replace(old_state, new_state)

# Add computed property for remaining balance
p_content = p_content.replace(
    "    get filteredProducts() {",
    '''    get remainingToPay() {
      const total = parseFloat(this.cart.totals.total || 0);
      const paid = this.payments.reduce((sum, p) => sum + (parseFloat(p.amount) || 0), 0);
      return parseFloat((total - paid).toFixed(2));
    },

    get filteredProducts() {'''
)

# Replace doCheckout function to handle split payments
old_do_checkout = '''    async doCheckout() {
      if (this.paymentMethod === 'CREDIT' && !this.customerId) {
        alert('Please select a registered customer to use Store Credit.'); return;
      }
      
      this.busy = true;
      let payment_reference = null;

      try {
        if (this.paymentMethod === 'MOMO') {
          if (!this.selectedProvider) { alert('Please select a network'); this.busy = false; return; }
          
          const initRes = await apiFetch('/payments/momo/initiate/', {
            method: 'POST',
            body: JSON.stringify({
              phone: this.paymentPhone,
              amount: this.cart.totals.total,
              provider: this.selectedProvider
            })
          });
          
          payment_reference = initRes.reference_id;
          this.pollingPayment = true;
          
          let isPaid = false;
          for (let i = 0; i < 30; i++) {
            await new Promise(r => setTimeout(r, 2000));
            const statusRes = await apiFetch(`/payments/momo/status/${payment_reference}/`);
            if (statusRes.status === 'SUCCESS') { isPaid = true; break; }
            if (statusRes.status === 'FAILED') { throw new Error('Payment declined or cancelled.'); }
          }
          
          this.pollingPayment = false;
          if (!isPaid) throw new Error('Payment timed out.');
        }

        // Perform Checkout
        const res = await apiFetch('/sales/cart/checkout/', {
          method: 'POST',
          body: JSON.stringify({ 
            payment_method: this.paymentMethod,
            payment_reference: payment_reference
          }),
        });
        
        // 1. Close checkout modal immediately
        this.checkoutOpen = false;
        this.pollingPayment = false;
        
        // 2. Fetch the receipt
        const receipt = await apiFetch(`/sales/invoices/${res.invoice_id}/receipt.txt`);
        
        // 3. Show the receipt modal
        this.receiptModal = { ...res, text: receipt.text };
        
        // 4. Clear the cart
        this.cart = { items: [], totals: {} };
        this.customerName = ''; this.customerId = null; this.customerPhone = ''; this.paymentPhone = '';
        this.payments = [{ method: 'CASH', amount: 0 }]; // Reset payments
        
        // 5. Refresh products
        this.products = await apiFetch('/inventory/products/');
        
      } catch (e) {
        this.pollingPayment = false;
        alert('Payment Error: ' + (e.response?.data?.error || e.message));
      } finally {
        this.busy = false;
      }
    },'''

new_do_checkout = '''    async doCheckout() {
      if (this.remainingToPay !== 0) { alert('Payment amount does not match the total.'); return; }
      
      this.busy = true;

      try {
        // Process each Mobile Money payment (initiate USSD and poll)
        for (let p of this.payments) {
          if (p.method === 'MOMO') {
            if (!this.paymentPhone) throw new Error('Phone number required for Mobile Money');
            
            const initRes = await apiFetch('/payments/momo/initiate/', {
              method: 'POST',
              body: JSON.stringify({
                phone: this.paymentPhone,
                amount: p.amount,
                provider: this.selectedProvider || 'MTN_DIRECT'
              })
            });
            
            const ref = initRes.reference_id;
            this.pollingPayment = true;
            
            let isPaid = false;
            for (let i = 0; i < 30; i++) {
              await new Promise(r => setTimeout(r, 2000));
              const statusRes = await apiFetch(`/payments/momo/status/${ref}/`);
              if (statusRes.status === 'SUCCESS') { isPaid = true; break; }
              if (statusRes.status === 'FAILED') { throw new Error('Payment declined.'); }
            }
            
            this.pollingPayment = false;
            if (!isPaid) throw new Error('Payment timed out.');
          }
        }

        // Submit the final checkout with the array of payments
        const res = await apiFetch('/sales/cart/checkout/', {
          method: 'POST',
          body: JSON.stringify({ payments: this.payments }),
        });
        
        this.checkoutOpen = false;
        this.pollingPayment = false;
        
        const receipt = await apiFetch(`/sales/invoices/${res.invoice_id}/receipt.txt`);
        this.receiptModal = { ...res, text: receipt.text };
        
        this.cart = { items: [], totals: {} };
        this.customerName = ''; this.customerId = null; this.customerPhone = ''; this.paymentPhone = '';
        this.payments = [{ method: 'CASH', amount: 0 }];
        
        this.products = await apiFetch('/inventory/products/');
        
      } catch (e) {
        this.pollingPayment = false;
        alert('Payment Error: ' + (e.response?.data?.error || e.message));
      } finally {
        this.busy = false;
      }
    },'''

if old_do_checkout in p_content:
    p_content = p_content.replace(old_do_checkout, new_do_checkout)
    print("✅ Updated doCheckout JS to handle multi-payments.")
else:
    print("⚠️ Could not find exact doCheckout block.")

# Auto-fill the first payment amount with the cart total when opening checkout
p_content = p_content.replace(
    '@click="checkoutOpen = true"',
    '@click="checkoutOpen = true; payments = [{ method: \'CASH\', amount: parseFloat(cart.totals.total || 0) }]"'
)

pos_path.write_text(p_content, encoding="utf-8")

print("\n🎉 Done! Restart the server and hard refresh the POS.")