import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# 1. Clean out any partial or broken receipt modals from previous attempts
# We look for anything between <!-- Receipt Modal --> and the next major script/div
content = re.sub(r"<!-- Receipt Modal -->.*?<script>", "<script>", content, flags=re.DOTALL)

# 2. Define the perfect Receipt Modal HTML
receipt_modal_html = """
    <!-- Receipt Modal -->
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
          <button @click="receiptModal = null; load();" class="btn-primary flex-1">
            Done
          </button>
        </div>
      </div>
    </div>
"""

# 3. Find the exact insertion point: right before the closing </div> of the x-data container
# We look for the last </div> before the <script> tag
pattern = r"(  </div>\s*</div>\s*<script>)"
if re.search(pattern, content):
    # Inject the modal before the closing tags
    content = re.sub(pattern, receipt_modal_html + r"\n\1", content, count=1)
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Successfully injected the Receipt Modal into the DOM.")
else:
    # Fallback just in case the structure is slightly different
    content = content.replace("</body>", receipt_modal_html + "\n</body>")
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Injected Receipt Modal at the end of the body.")

# 4. Double check the JS flow to ensure `receiptModal` is triggered correctly
if "this.receiptModal = { ...res, text: receipt.text };" not in content:
    print("⚠️ Checkout JS might have been modified. Re-applying safe receipt logic...")
    # (If the JS was messed up, we re-apply the safe block)
    old_js = r"const receipt = await apiFetch\(`/sales/invoices/\$\{res\.invoice_id\}/receipt\.txt`\);.*?this\.products = await apiFetch\('/inventory/products/'\);"
    new_js = """const receipt = await apiFetch(`/sales/invoices/${res.invoice_id}/receipt.txt`);
        
        // Close checkout, show receipt
        this.checkoutOpen = false;
        this.pollingPayment = false;
        this.receiptModal = { ...res, text: receipt.text };
        
        // Clear cart
        this.cart = { items: [], totals: {} };
        this.customerName = ''; this.customerId = null; this.paymentPhone = '';
        this.paymentMethod = 'CASH';
        
        // Refresh products
        this.products = await apiFetch('/inventory/products/');"""
    
    content = re.sub(old_js, new_js.strip(), content, flags=re.DOTALL)
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Re-applied safe receipt logic.")

print("\n🎉 Done! Restart the server and do a hard refresh (Ctrl + Shift + R).")