import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# Find the doCheckout function and inject the product refresh and success message
old_checkout_logic = """        const receipt = await apiFetch(`/sales/invoices/${res.invoice_id}/receipt.txt`);
        this.receiptModal = { ...res, text: receipt.text };
        this.cart = { items: [], totals: {} };
        this.customerName = ''; this.customerId = null; this.paymentPhone = '';
        this.checkoutOpen = false;
        this.paymentMethod = 'CASH';
        
      } catch (e) {"""

new_checkout_logic = """        const receipt = await apiFetch(`/sales/invoices/${res.invoice_id}/receipt.txt`);
        
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

if old_checkout_logic in content:
    content = content.replace(old_checkout_logic, new_checkout_logic)
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Updated POS UI to refresh stock and show success message.")
else:
    print("⚠️ Could not find the checkout logic block. Please ensure the file hasn't been manually modified.")