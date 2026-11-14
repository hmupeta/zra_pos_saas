import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# 1. Remove the annoying alert() and fix the checkout flow
old_checkout = """        const receipt = await apiFetch(`/sales/invoices/${res.invoice_id}/receipt.txt`);
        
        // 1. Show the receipt
        this.receiptModal = { ...res, text: receipt.text };
        
        // 2. Clear the cart
        this.cart = { items: [], totals: {} };
        this.customerName = ''; this.customerId = null; this.paymentPhone = '';
        this.checkoutOpen = false;
        this.paymentMethod = 'CASH';
        
        // 3. Refresh the product list so the new stock quantities are visible!
        this.products = await apiFetch('/inventory/products/');
        
        // 4. Alert the cashier (in case the modal is hidden)
        alert(`Sale successful! Invoice: ${res.invoice_number}`);
        
      } catch (e) {"""

new_checkout = """        // 1. Close the checkout modal immediately
        this.checkoutOpen = false;
        this.pollingPayment = false;
        
        // 2. Fetch the receipt text
        const receipt = await apiFetch(`/sales/invoices/${res.invoice_id}/receipt.txt`);
        
        // 3. Show the receipt modal
        this.receiptModal = { ...res, text: receipt.text };
        
        // 4. Clear the cart and reset fields
        this.cart = { items: [], totals: {} };
        this.customerName = ''; this.customerId = null; this.paymentPhone = '';
        this.paymentMethod = 'CASH';
        
        // 5. Refresh the product list so new stock quantities are visible
        this.products = await apiFetch('/inventory/products/');
        
      } catch (e) {"""

content = content.replace(old_checkout, new_checkout)

# 2. Ensure the Receipt Modal is at the bottom of the DOM and has a high z-index
# First, remove any existing receipt modal
receipt_modal_pattern = r"<!-- Receipt Modal -->.*?</div>\s*</div>\s*</div>"
content = re.sub(receipt_modal_pattern, "", content, flags=re.DOTALL)

# Insert the Receipt Modal right before the closing </div> of the main container
new_receipt_modal = """
    <!-- Receipt Modal -->
    <div x-show="receiptModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-[100] p-4">
      <div class="bg-white rounded-xl max-w-md w-full max-h-[90vh] flex flex-col shadow-2xl">
        <div class="p-4 border-b flex justify-between items-center bg-gray-50 rounded-t-xl">
          <h2 class="text-lg font-bold">Receipt</h2>
          <button @click="receiptModal = null" class="text-gray-400 hover:text-gray-600">
            <i data-lucide="x" class="w-5 h-5"></i>
          </button>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          <pre class="receipt-text bg-gray-50 p-4 rounded-lg" x-text="receiptModal?.text"></pre>
        </div>
        <div class="p-4 border-t flex gap-2">
          <button @click="printReceipt(receiptModal.text)" class="btn-secondary flex-1 flex items-center justify-center gap-2">
            <i data-lucide="printer" class="w-4 h-4"></i> Print
          </button>
          <button @click="receiptModal = null" class="btn-primary flex-1">Done</button>
        </div>
      </div>
    </div>
"""

# Find the end of the main x-data div and insert the modal there
content = content.replace("  </div>\n</div>\n\n<script>", new_receipt_modal + "\n  </div>\n</div>\n\n<script>")
pos_path.write_text(content, encoding="utf-8")

print("✅ Fixed checkout flow to properly display receipt.")
print("🎉 Done! Restart the server and refresh your browser.")