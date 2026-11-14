import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# 1. Force replace the entire doCheckout function using regex
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

# Find the doCheckout function and replace it up to the next function or end
pattern = r"    async doCheckout\(\) \{.*?\n    \},"
if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_do_checkout, content, count=1, flags=re.DOTALL)
    print("✅ Forcefully replaced doCheckout function.")
else:
    print("⚠️ Regex failed. Checking for other variations...")
    # Fallback, just in case
    start = content.find("async doCheckout() {")
    if start != -1:
        end = content.find("    },", start)
        if end != -1:
            content = content[:start] + new_do_checkout + content[end+7:]
            print("✅ Replaced using manual string slicing.")

# 2. Ensure remainingToPay getter exists
if "get remainingToPay()" not in content:
    getter = '''
    get remainingToPay() {
      const total = parseFloat(this.cart.totals.total || 0);
      const paid = this.payments.reduce((sum, p) => sum + (parseFloat(p.amount) || 0), 0);
      return parseFloat((total - paid).toFixed(2));
    },
'''
    content = content.replace("    get filteredProducts() {", getter + "\n    get filteredProducts() {")
    print("✅ Injected remainingToPay getter.")

# 3. Ensure the Checkout button resets the payments array when clicked
old_btn = '@click="checkoutOpen = true"'
new_btn = '@click="checkoutOpen = true; payments = [{ method: \'CASH\', amount: parseFloat(cart.totals.total || 0) }]"'
if old_btn in content and new_btn not in content:
    content = content.replace(old_btn, new_btn)
    print("✅ Updated Checkout button to auto-fill first payment.")

pos_path.write_text(content, encoding="utf-8")
print("\n🎉 Done! Restart the server and do a HARD REFRESH on the POS.")