import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# ============================================================
# 1. Remove the old broken Discount Modal HTML (we use auto-discounts now)
# ============================================================
discount_modal_pattern = r"<!-- Discount Modal -->.*?</div>\s*</div>\s*</div>"
content = re.sub(discount_modal_pattern, "", content, flags=re.DOTALL)

# ============================================================
# 2. Completely replace the JavaScript block
# ============================================================
new_js = """
<script>
function posScreen() {
  return {
    shift: null, products: [], cart: { items: [], totals: {} },
    search: '', busy: false, lastScan: null, customerName: '', customerId: null,
    customerSearch: '', customerResults: [], showCustDropdown: false, showNewCustModal: false,
    newCust: { first_name: '', last_name: '', phone_number: '' },
    openShiftModal: false, checkoutOpen: false, receiptModal: null, 
    paymentMethod: 'CASH', paymentPhone: '', pollingPayment: false,
    availableMomoProviders: [], selectedProvider: '', paymentConfigs: [],
    zReportModal: false, zReportData: {}, actualCash: 0, variance: 0,
    openingBalance: 0,

    async init() {
      if (!requireAuth() || !requireBranch()) return;

      window.addEventListener('barcode-scanned', (e) => this.scanAdd(e.detail.code));

      try {
        this.shift = await apiFetch('/sales/current-shift/').catch((e) => {
          if (e.response?.status === 404) return null; throw e;
        });
        this.products = await apiFetch('/inventory/products/');

        if (this.shift) {
          this.cart = await apiFetch('/sales/cart/');
        } else {
          this.openShiftModal = true;
        }

        // Load payment gateways
        try {
          this.paymentConfigs = await apiFetch('/payments/configs/');
          if (this.paymentConfigs && Array.isArray(this.paymentConfigs)) {
            const momoConfigs = this.paymentConfigs.filter(c => c.provider.includes('DIRECT'));
            this.availableMomoProviders = [...new Set(momoConfigs.map(c => c.provider))];
            if (this.availableMomoProviders.length > 0) {
              this.selectedProvider = this.availableMomoProviders[0];
            }
          }
        } catch (e) { console.error("Could not load gateways", e); }

        const branches = await apiFetch('/auth/branches/');
        const cur = branches.find(b => String(b.id) === String(getBranchId()));
        if (cur) document.getElementById('pos-branch').textContent = cur.name;
      } catch (e) {
        alert('Failed to load POS: ' + e.message);
      }
    },

    get filteredProducts() {
      const q = this.search.toLowerCase();
      return q ? this.products.filter(p => p.name.toLowerCase().includes(q) || p.barcode.includes(q)) : this.products;
    },

    formatProviderName(p) {
      if (!p) return '';
      const names = { 
        'MTN_DIRECT': 'MTN Mobile Money', 
        'AIRTEL_DIRECT': 'Airtel Money', 
        'ZAMTEL_DIRECT': 'Zamtel Kwacha' 
      };
      return names[p] || p;
    },

    async scanAdd(barcode) {
      if (!this.shift) { alert('Open a shift first'); return; }
      try {
        const res = await apiFetch('/sales/scan-add/', {
          method: 'POST',
          body: JSON.stringify({ barcode, quantity: 1 }),
        });
        this.cart = res.cart;
        this.lastScan = res.product.barcode;
        setTimeout(() => this.lastScan = null, 700);
      } catch (e) {
        alert(e.response?.data?.error || 'Scan failed');
      }
    },

    async openShift() {
      try {
        await apiFetch('/sales/open-shift/', {
          method: 'POST',
          body: JSON.stringify({ opening_balance: parseFloat(this.openingBalance) || 0 }),
        });
        this.shift = await apiFetch('/sales/current-shift/');
        this.openShiftModal = false;
      } catch (e) { alert(e.response?.data?.error || 'Failed'); }
    },

    async clearCart() {
      if (!confirm('Clear cart?')) return;
      try {
        await apiFetch('/sales/cart/clear/', { method: 'POST' });
        this.cart = { items: [], totals: {} };
      } catch (e) { alert('Failed'); }
    },

    async doCheckout() {
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
        this.customerName = ''; this.customerId = null; this.paymentPhone = '';
        this.checkoutOpen = false;
        this.paymentMethod = 'CASH';
        
      } catch (e) {
        this.pollingPayment = false;
        alert('Payment Error: ' + (e.response?.data?.error || e.message));
      } finally {
        this.busy = false;
      }
    },

    async openZReport() {
      try {
        this.zReportData = await apiFetch('/sales/shift/summary/');
        this.actualCash = this.zReportData.expected_cash;
        this.calculateVariance();
        this.zReportModal = true;
      } catch(e) { alert(e.message); }
    },

    calculateVariance() {
      this.variance = parseFloat(this.actualCash || 0) - parseFloat(this.zReportData.expected_cash || 0);
    },

    async submitCloseShift() {
      if (!confirm('Are you sure you want to close this shift?')) return;
      try {
        const res = await apiFetch('/sales/close-shift/', {
          method: 'POST',
          body: JSON.stringify({ actual_cash: this.actualCash })
        });
        alert(`Shift closed. Variance: ${formatCurrency(res.variance)}`);
        this.zReportModal = false;
        this.shift = null;
        this.cart = { items: [], totals: {} };
        this.openShiftModal = true;
      } catch(e) { alert(e.message); }
    }
  }
}
</script>
"""

# Replace the existing <script> block containing posScreen()
pattern = r"<script>\s*function posScreen\(\) \{.*?</script>"
content = re.sub(pattern, new_js.strip(), content, flags=re.DOTALL)
pos_path.write_text(content, encoding="utf-8")
print("✅ Completely rebuilt the POS JavaScript state and methods.")
print("🎉 Done! Restart the server and hard refresh.")