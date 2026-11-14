from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
cart_file = BACKEND_PATH / "sales" / "cart_service.py"

new_cart_code = '''
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
        
        price_gross = Decimal(str(product_data["selling_price"]))
        tax_rate = Decimal(str(product_data["tax_rate"]))
        
        if existing:
            new_qty = Decimal(str(existing["quantity"])) + qty
            existing["quantity"] = float(new_qty)
            
            # --- VAT INCLUSIVE MATH ---
            line_total_gross = new_qty * price_gross
            line_subtotal_net = line_total_gross / (1 + (tax_rate / 100))
            line_tax = line_total_gross - line_subtotal_net
            
            existing["line_total"] = float(line_total_gross)
            existing["line_subtotal_net"] = float(line_subtotal_net)
            existing["tax_amount"] = float(line_tax)
        else:
            # --- VAT INCLUSIVE MATH ---
            line_total_gross = qty * price_gross
            line_subtotal_net = line_total_gross / (1 + (tax_rate / 100))
            line_tax = line_total_gross - line_subtotal_net
            
            cart["items"].append({
                "product_id": product_data["id"],
                "barcode": product_data["barcode"],
                "name": product_data["name"],
                "quantity": float(qty),
                "unit_price": float(price_gross),
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
        total = sum(Decimal(str(i.get("line_total", 0))) for i in cart["items"])
        
        return {"subtotal": float(sub), "tax_total": float(tax), "total": float(total),
                "item_count": len(cart["items"])}

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
            subtotal=totals["subtotal"], tax_total=totals["tax_total"],
            total=totals["total"], status="PAID", payment_method=payment_method,
        )
        
        for item in cart["items"]:
            p = Product.objects.select_for_update().get(pk=item["product_id"])
            InvoiceItem.objects.create(
                invoice=invoice, product=p,
                quantity=item["quantity"], unit_price=item["unit_price"],
                tax_rate=item["tax_rate"], tax_amount=item["tax_amount"],
                total=item["line_total"], zra_item_code=item["zra_item_code"],
            )
            p.current_stock -= Decimal(str(item["quantity"]))
            p.save(update_fields=["current_stock"])
            BarcodeService.invalidate(tenant_id, branch_id, p.barcode)
            
        CartService.clear(tenant_id, branch_id, shift.id)
        return invoice
'''

cart_file.write_text(new_cart_code.strip(), encoding="utf-8")
print("✅ Rebuilt sales/cart_service.py with VAT Inclusive Math.")