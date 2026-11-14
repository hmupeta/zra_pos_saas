import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Rebuild cart_service.py
# ============================================================
cart_file = BACKEND_PATH / "sales" / "cart_service.py"

correct_code = '''
from decimal import Decimal
from django.core.cache import cache
from django.db import transaction
from .models import Invoice, InvoiceItem
from inventory.models import Product
from inventory.services import BarcodeService

CART_TTL = 4 * 3600


class CartService:
    @staticmethod
    def _key(tenant_id, branch_id, shift_id):
        return f"cart:{tenant_id}:{branch_id}:{shift_id}"

    @staticmethod
    def get(tenant_id, branch_id, shift_id):
        return cache.get(CartService._key(tenant_id, branch_id, shift_id)) or {"items": []}

    @staticmethod
    def save(tenant_id, branch_id, shift_id, cart):
        cache.set(CartService._key(tenant_id, branch_id, shift_id), cart, CART_TTL)

    @staticmethod
    def add_item(tenant_id, branch_id, shift_id, product_data, quantity=1):
        cart = CartService.get(tenant_id, branch_id, shift_id)
        qty = Decimal(str(quantity))
        
        existing = next((i for i in cart["items"] if i["barcode"] == product_data["barcode"]), None)
        
        original_price = Decimal(str(product_data["selling_price"]))
        discount_pct = Decimal(str(product_data.get("discount_percentage", 0)))
        
        # Calculate discounted price
        if discount_pct > 0:
            discount_amt = original_price * (discount_pct / 100)
            price_gross = original_price - discount_amt
        else:
            price_gross = original_price
            
        tax_rate = Decimal(str(product_data["tax_rate"]))
        
        if existing:
            new_qty = Decimal(str(existing["quantity"])) + qty
            existing["quantity"] = float(new_qty)
            
            # Recalculate totals based on discounted price
            line_total_gross = new_qty * price_gross
            line_subtotal_net = line_total_gross / (1 + (tax_rate / 100))
            line_tax = line_total_gross - line_subtotal_net
            
            existing["line_total"] = float(line_total_gross)
            existing["line_subtotal_net"] = float(line_subtotal_net)
            existing["tax_amount"] = float(line_tax)
        else:
            line_total_gross = qty * price_gross
            line_subtotal_net = line_total_gross / (1 + (tax_rate / 100))
            line_tax = line_total_gross - line_subtotal_net
            
            cart["items"].append({
                "product_id": product_data["id"],
                "barcode": product_data["barcode"],
                "name": product_data["name"],
                "quantity": float(qty),
                "unit_price": float(original_price),
                "price_gross": float(price_gross),
                "discount_percentage": float(discount_pct),
                "tax_rate": float(tax_rate),
                "line_subtotal_net": float(line_subtotal_net),
                "tax_amount": float(line_tax),
                "line_total": float(line_total_gross),
                "zra_item_code": product_data.get("zra_item_code", ""),
            })
            
        CartService.save(tenant_id, branch_id, shift_id, cart)
        return cart

    @staticmethod
    def totals(cart):
        sub = sum(Decimal(str(i.get("line_subtotal_net", 0))) for i in cart["items"])
        tax = sum(Decimal(str(i.get("tax_amount", 0))) for i in cart["items"])
        gross = sum(Decimal(str(i.get("line_total", 0))) for i in cart["items"])
        
        return {
            "subtotal": float(sub),
            "tax_total": float(tax),
            "total": float(gross),
            "item_count": len(cart["items"])
        }

    @staticmethod
    def clear(tenant_id, branch_id, shift_id):
        cache.delete(CartService._key(tenant_id, branch_id, shift_id))

    @staticmethod
    @transaction.atomic
    def checkout(tenant_id, branch_id, shift, cashier, payment_method="CASH"):
        cart = CartService.get(tenant_id, branch_id, shift.id)
        if not cart["items"]:
            raise ValueError("Cart is empty")
            
        totals = CartService.totals(cart)
        import datetime
        inv_num = f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
        
        invoice = Invoice.objects.create(
            invoice_number=inv_num, tenant_id=tenant_id, company_id=branch_id,
            shift=shift, cashier=cashier,
            customer_name=cart.get("customer_name", "Cash Customer"),
            customer_id=cart.get("customer_id"),
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            total=totals["total"], status="PAID", payment_method=payment_method,
        )
        
        for item in cart["items"]:
            p = Product.objects.select_for_update().get(pk=item["product_id"])
            InvoiceItem.objects.create(
                invoice=invoice, product=p,
                quantity=item["quantity"], unit_price=item["price_gross"],
                tax_rate=item["tax_rate"], tax_amount=item["tax_amount"],
                total=item["line_total"], zra_item_code=item["zra_item_code"],
            )
            p.current_stock -= Decimal(str(item["quantity"]))
            p.save(update_fields=["current_stock"])
            BarcodeService.invalidate(tenant_id, branch_id, p.barcode)
            
        # Award Loyalty Points
        if invoice.customer:
            points_earned = int(invoice.total / 10)
            invoice.customer.loyalty_points += points_earned
            invoice.customer.total_spent += invoice.total
            invoice.customer.save()
            
        CartService.clear(tenant_id, branch_id, shift.id)
        return invoice
'''
cart_file.write_text(correct_code.strip(), encoding="utf-8")
print("✅ Rebuilt sales/cart_service.py successfully")

# ============================================================
# 2. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "inventory"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")