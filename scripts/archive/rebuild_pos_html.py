import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

# We are rewriting the entire file to guarantee perfect HTML structure and JS state.
full_html = '''
{% extends "pos/base.html" %}
{% block title %}POS · Sale{% endblock %}
{% block body %}
<div class="h-screen flex" x-data="posScreen()" x-init="init()">

  <!-- Sidebar -->
  {% include "pos/_nav.html" %}

  <!-- Main -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <header class="h-14 bg-white border-b flex items-center justify-between px-4">
      <div class="text-sm font-medium" id="pos-branch">Branch</div>
      <div class="text-xs px-2 py-1 rounded-full"
           :class="shift ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
           x-text="shift ? 'Scanner ready' : 'Shift closed'"></div>
    </header>

    <div class="flex-1 flex overflow-hidden">
      <!-- Products grid -->
      <div class="flex-1 p-4 overflow-y-auto">
        <div class="mb-4">
          <input type="text" x-model="search" placeholder="Search products or scan..."
                 class="input-field" />
        </div>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          <template x-for="p in filteredProducts" :key="p.id">
            <button @click="scanAdd(p.barcode)"
                    :class="lastScan === p.barcode ? 'flash-green' : ''"
                    class="card p-3 text-left hover:shadow-md hover:border-brand-500 transition">
              <div class="font-medium text-sm line-clamp-2 h-10" x-text="p.name"></div>
              <div class="text-xs text-gray-500 mt-1" x-text="p.barcode"></div>
              <div class="flex justify-between items-end mt-2">
                <div class="text-lg font-bold text-brand-700" x-text="formatCurrency(p.selling_price)"></div>
                <div class="text-xs text-gray-400">Stock <span x-text="p.current_stock"></span></div>
              </div>
            </button>
          </template>
        </div>
        <div x-show="filteredProducts.length === 0" class="text-center py-12 text-gray-400">
          No products found
        </div>
      </div>

      <!-- Cart -->
      <div class="w-96 bg-white border-l flex flex-col relative z-10">
        <div class="p-4 border-b flex justify-between items-center">
          <h2 class="font-semibold">Cart (<span x-text="cart.totals.item_count || 0"></span>)</h2>
          <button x-show="cart.items?.length > 0" @click="clearCart()" class="text-xs text-red-600">Clear</button>
        </div>
        
        <!-- Customer Search -->
        <div class="px-4 py-2 border-b bg-gray-50 relative">
          <div class="flex gap-2">
            <input type="text" x-model="customerSearch" @input.debounce.300ms="searchCustomers()" @focus="showCustDropdown = true" placeholder="Search Phone or Name..." class="w-full px-2 py-1 text-sm border rounded">
            <button @click="showNewCustModal = true" class="bg-brand-100 text-brand-700 px-2 rounded text-sm font-bold hover:bg-brand-200" title="Add New Customer">+</button>
          </div>
          
          <template x-if="customerName">
            <div class="mt-2 flex justify-between items-center bg-green-50 px-2 py-1 rounded border border-green-200">
              <span class="text-xs font-medium text-green-800" x-text="customerName"></span>
              <button @click="clearCustomer()" class="text-green-600 hover:text-green-900 text-xs font-bold">✕</button>
            </div>
          </template>

          <div x-show="showCustDropdown && customerResults.length > 0" @click.away="showCustDropdown = false" class="absolute left-0 right-0 mt-1 bg-white border shadow-lg rounded z-20 mx-4 max-h-48 overflow-y-auto">
            <template x-for="c in customerResults" :key="c.id">
              <div @click="selectCustomer(c)" class="p-2 border-b hover:bg-gray-50 cursor-pointer">
                <div class="text-sm font-medium" x-text="c.name"></div>
                <div class="text-xs text-gray-500"><span x-text="c.phone"></span> · Points: <span x-text="c.points"></span></div>
              </div>
            </template>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-4 space-y-2">
          <template x-if="!cart.items || cart.items.length === 0">
            <div class="text-center py-12 text-gray-400">Scan or click products</div>
          </template>
          <template x-for="item in cart.items || []" :key="item.barcode">
            <div class="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate" x-text="item.name"></div>
                <div class="text-xs text-gray-500">
                  <template x-if="item.discount_percentage > 0">
                    <span>
                      <span class="line-through text-gray-400" x-text="formatCurrency(item.unit_price)"></span>
                      <span class="text-red-600 font-bold ml-1" x-text="formatCurrency(item.price_gross)"></span>
                    </span>
                  </template>
                  <template x-if="item.discount_percentage === 0">
                    <span x-text="formatCurrency(item.unit_price)"></span>
                  </template>
                  × <span x-text="item.quantity"></span>
                </div>
              </div>
              <div class="text-sm font-semibold" x-text="formatCurrency(item.line_total)"></div>
            </div>
          </template>
        </div>

        <div class="p-4 border-t space-y-3">
          <div class="flex justify-between text-sm">
            <span class="text-gray-500">Subtotal</span>
            <span x-text="formatCurrency(cart.totals.subtotal || 0)"></span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-500">VAT</span>
            <span x-text="formatCurrency(cart.totals.tax_total || 0)"></span>
          </div>
          <div class="flex justify-between text-lg font-bold pt-2 border-t">
            <span>Total</span>
            <span class="text-brand-700" x-text="formatCurrency(cart.totals.total || 0)"></span>
          </div>
          <button :disabled="!shift || !cart.items || cart.items.length === 0"
                  @click="checkoutOpen = true" class="btn-primary w-full py-3 text-base">
            Checkout
          </button>
          <button x-show="shift" @click="openZReport()" class="btn-secondary w-full text-sm text-red-600 border-red-200 hover:bg-red-50">
            End Shift (Z-Report)
          </button>
        </div>
      </div>
    </div>
  </div>

  <!-- Open Shift Modal -->
  <div x-show="openShiftModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-xl max-w-md w-full p-6">
      <h2 class="text-xl font-bold mb-4">Open Shift</h2>
      <label class="block text-sm font-medium mb-1">Opening balance (cash in drawer)</label>
      <input type="number" x-model="openingBalance" class="input-field mb-4" />
      <button @click="openShift()" class="btn-primary w-full">Open Shift</button>
    </div>
  </div>

  <!-- Checkout Modal -->
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
  </div>

  <!-- Polling Modal -->
  <div x-show="pollingPayment" x-cloak class="fixed inset-0 bg-black/80 flex items-center justify-center z-[60] p-4">
    <div class="bg-white rounded-xl max-w-sm w-full p-8 text-center shadow-2xl">
      <div class="animate-spin rounded-full h-16 w-16 border-b-4 border-brand-600 mx-auto mb-6"></div>
      <h2 class="text-xl font-bold text-slate-900 mb-2">Waiting for Payment</h2>
      <p class="text-gray-500 mb-6">A prompt has been sent to <strong x-text="paymentPhone"></strong>. Please enter your PIN to authorize.</p>
      <button @click="pollingPayment = false; busy = false" class="text-red-600 text-sm hover:underline">Cancel Transaction</button>
    </div>
  </div>

  <!-- Receipt Modal (Extreme Z-Index) -->
  <div x-show="receiptModal" x-cloak class="fixed inset-0 bg-black/60 flex items-center justify-center z-[9999] p-4 backdrop-blur-sm">
    <div class="bg-white rounded-xl max-w-md w-full max-h-[90vh] flex flex-col shadow-2xl" @click.away="receiptModal = null">
      <div class="p-4 border-b flex justify-between items-center bg-gray-50 rounded-t-xl">
        <h2 class="text-lg font-bold text-slate-800 flex items-center gap-2">
          <i data-lucide="receipt" class="w-5 h-5 text-brand-600"></i> Receipt
        </h2>
        <button @click="receiptModal = null" class="text-gray-400 hover:text-gray-600">
          <i data-lucide="x" class="w-5 h-5"></i>
        </button>
      </div>
      <div class="flex-1 overflow-y-auto p-4 bg-gray-100">
        <pre class="receipt-text bg-white p-4 rounded shadow-sm text-sm" x-text="receiptModal?.text"></pre>
      </div>
      <div class="p-4 border-t flex gap-2 bg-gray-50 rounded-b-xl">
        <button @click="printReceipt(receiptModal.text)" class="btn-secondary flex-1 flex items-center justify-center gap-2">
          <i data-lucide="printer" class="w-4 h-4"></i> Print
        </button>
        <button @click="receiptModal = null;" class="btn-primary flex-1">
          Done
        </button>
      </div>
    </div>
  </div>

  <!-- Z-Report Modal -->
  <div x-show="zReportModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-xl max-w-md w-full p-6">
      <h2 class="text-xl font-bold mb-4">End of Shift (Z-Report)</h2>
      <div class="space-y-2 text-sm mb-4 bg-gray-50 p-4 rounded-lg">
        <div class="flex justify-between"><span class="text-gray-500">Total Sales:</span><span class="font-bold" x-text="formatCurrency(zReportData.total_sales)"></span></div>
        <div class="flex justify-between"><span class="text-gray-500">Transactions:</span><span x-text="zReportData.transaction_count"></span></div>
        <div class="flex justify-between border-t pt-2 mt-2"><span class="text-gray-500">Cash Sales:</span><span x-text="formatCurrency(zReportData.cash_sales)"></span></div>
        <div class="flex justify-between border-t pt-2 mt-2 font-bold"><span>Expected Cash:</span><span class="text-brand-700" x-text="formatCurrency(zReportData.expected_cash)"></span></div>
      </div>
      <label class="block text-sm font-medium mb-1">Physical Cash Counted</label>
      <input type="number" step="0.01" x-model="actualCash" @input="calculateVariance()" class="input-field mb-2 text-lg font-bold">
      <div class="mb-4 p-2 rounded text-center text-sm font-bold" :class="variance < 0 ? 'bg-red-100 text-red-700' : variance > 0 ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-600'">
        <span x-text="variance === 0 ? 'Perfectly balanced' : (variance < 0 ? 'Shortage: ' : 'Overage: ') + formatCurrency(Math.abs(variance))"></span>
      </div>
      <div class="flex gap-2">
        <button @click="zReportModal = false" class="btn-secondary flex-1">Cancel</button>
        <button @click="submitCloseShift()" class="btn-primary flex-1 bg-red-600 hover:bg-red-700 text-white">Confirm & Close</button>
      </div>
    </div>
  </div>

  <!-- New Customer Modal -->
  <div x-show="showNewCustModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-xl max-w-sm w-full p-6">
      <h2 class="text-xl font-bold mb-4">New Customer</h2>
      <form @submit.prevent="createNewCustomer()" class="space-y-3">
        <input type="text" x-model="newCust.phone_number" placeholder="Phone Number" class="input-field" required>
        <input type="text" x-model="newCust.first_name" placeholder="First Name" class="input-field" required>
        <input type="text" x-model="newCust.last_name" placeholder="Last Name" class="input-field">
        <div class="flex gap-2 mt-4">
          <button type="button" @click="showNewCustModal = false" class="btn-secondary flex-1">Cancel</button>
          <button type="submit" class="btn-primary flex-1">Save</button>
        </div>
      </form>
    </div>
  </div>

</div>

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

    // --- Customer Search ---
    async searchCustomers() {
      if (this.customerSearch.length < 3) { this.customerResults = []; return; }
      try {
        this.customerResults = await apiFetch(`/customers/pos-search/?q=${this.customerSearch}`);
        this.showCustDropdown = true;
      } catch(e) { console.error(e); }
    },

    selectCustomer(c) {
      this.customerId = c.id;
      this.customerName = c.name;
      this.customerSearch = '';
      this.customerResults = [];
      this.showCustDropdown = false;
      this.updateCustomer();
    },

    clearCustomer() {
      this.customerId = null;
      this.customerName = '';
      this.updateCustomer();
    },

    async createNewCustomer() {
      try {
        const res = await apiFetch('/customers/', { method: 'POST', body: JSON.stringify(this.newCust) });
        this.selectCustomer({ id: res.id, name: res.name });
        this.showNewCustModal = false;
        this.newCust = { first_name: '', last_name: '', phone_number: '' };
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },

    async updateCustomer() {
      if (!this.shift) return;
      try {
        await apiFetch('/sales/cart/customer/', {
          method: 'POST',
          body: JSON.stringify({ customer_id: this.customerId, customer_name: this.customerName })
        });
      } catch (e) { console.error('Failed to update customer', e); }
    },

    // --- Checkout ---
    async doCheckout() {
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
        this.customerName = ''; this.customerId = null; this.paymentPhone = '';
        this.paymentMethod = 'CASH';
        
        // 5. Refresh products
        this.products = await apiFetch('/inventory/products/');
        
      } catch (e) {
        this.pollingPayment = false;
        alert('Payment Error: ' + (e.response?.data?.error || e.message));
      } finally {
        this.busy = false;
      }
    },

    printReceipt(text) {
      const win = window.open('', '_blank', 'width=400,height=650');
      if (!win) { alert('Allow popups to print receipts'); return; }
      win.document.write(`<html><head><title>Receipt</title><style>body{font-family:'Courier New',monospace;font-size:12px;margin:8px;}pre{white-space:pre-wrap;margin:0;}@media print{body{margin:0;}}</style></head><body><pre>${text}</pre><script>window.onload=()=>{window.print();setTimeout(()=>window.close(),100);}</script></body></html>`);
      win.document.close();
    },

    // --- Z-Report ---
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
{% endblock %}
'''

pos_path.write_text(full_html.strip() + "\n", encoding="utf-8")
print("✅ Completely rebuilt pos.html with perfect structure and receipt modal.")
print("🎉 Done! Restart the server and do a hard refresh (Ctrl + Shift + R).")