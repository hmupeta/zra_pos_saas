import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Completely rewrite sales/cart_service.py
# ============================================================
cart_file = BACKEND_PATH / "sales" / "cart_service.py"

correct_code = '''
import uuid
import datetime
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
        
        if discount_pct > 0:
            discount_amt = original_price * (discount_pct / 100)
            price_gross = original_price - discount_amt
        else:
            price_gross = original_price
            
        tax_rate = Decimal(str(product_data["tax_rate"]))
        
        if existing:
            new_qty = Decimal(str(existing["quantity"])) + qty
            existing["quantity"] = float(new_qty)
            
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
    def checkout(tenant_id, branch_id, shift, cashier, payments_data):
        cart = CartService.get(tenant_id, branch_id, shift.id)
        if not cart["items"]:
            raise ValueError("Cart is empty")

        totals = CartService.totals(cart)
        grand_total = Decimal(str(totals["total"]))
        
        # Validate Payments
        total_paid = sum(Decimal(str(p["amount"])) for p in payments_data)
        if total_paid < grand_total:
            raise ValueError(f"Insufficient payment. Total is {grand_total}, but only {total_paid} was provided.")
        if total_paid > grand_total:
            raise ValueError("Payment amount exceeds the cart total.")

        inv_num = f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-{uuid.uuid4().hex[:4].upper()}"
        
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

        # Create Payment Transactions
        from payments.models import PaymentTransaction
        for p in payments_data:
            PaymentTransaction.objects.create(
                invoice=invoice, payment_method=p["method"],
                amount=Decimal(str(p["amount"])), status="SUCCESS"
            )

        # Create Invoice Items & Update Stock
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

        # Update Customer Stats
        if customer_id:
            from customers.models import Customer
            customer = Customer.objects.select_for_update().get(pk=customer_id)
            customer.total_spent += invoice.total
            points_earned = int(invoice.total / 10)
            customer.loyalty_points += points_earned
            customer.save()

        # Post Accounting
        from accounting.models import Account, Journal, JournalLine
        sales_acct = Account.objects.filter(tenant_id=tenant_id, code="4000").first()
        vat_acct = Account.objects.filter(tenant_id=tenant_id, code="2100").first()
        
        if sales_acct and vat_acct:
            journal = Journal.objects.create(
                tenant_id=tenant_id, company_id=branch_id, journal_number=f"JV-{inv_num}",
                date=datetime.date.today(), description=f"Sale {inv_num}", journal_type="SALES",
                status="POSTED", source_invoice=invoice, created_by=cashier
            )
            
            for p in payments_data:
                if p["method"] == "CASH":
                    debit_acct = Account.objects.filter(tenant_id=tenant_id, code="1000").first()
                elif p["method"] in ("MOMO", "MTN", "AIRTEL", "ZAMTEL", "CARD"):
                    debit_acct = Account.objects.filter(tenant_id=tenant_id, code="1010").first()
                else:
                    debit_acct = Account.objects.filter(tenant_id=tenant_id, code="1000").first()
                
                if debit_acct:
                    JournalLine.objects.create(journal=journal, account=debit_acct, debit=Decimal(str(p["amount"])), description=f"{p['method']} Payment")

            JournalLine.objects.create(journal=journal, account=sales_acct, credit=invoice.subtotal)
            if invoice.tax_total > 0:
                JournalLine.objects.create(journal=journal, account=vat_acct, credit=invoice.tax_total)

        CartService.clear(tenant_id, branch_id, shift.id)
        return invoice
'''
cart_file.write_text(correct_code.strip(), encoding="utf-8")
print("✅ Completely rebuilt sales/cart_service.py with split payment logic.")

# ============================================================
# 2. Patch sales/views.py to accept payments array
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Find the checkout view
pattern = r"@api_view\(\[\"POST\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef checkout\(request\):.*?return Response\(\{\"error\": str\(e\)\}, status=400\)"

new_checkout_view = '''
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=400)
        
    payments = request.data.get("payments", [])
    if not payments:
        return Response({"error": "No payment details provided"}, status=400)

    try:
        invoice = CartService.checkout(
            request.tenant.id, request.branch.id, shift, request.user,
            payments
        )
        return Response({
            "success": True,
            "invoice_id": invoice.id,
            "invoice_number": invoice.invoice_number,
            "total": float(invoice.total),
            "zra_code": invoice.zra_validation_code
        })
    except ValueError as e:
        return Response({"error": str(e)}, status=400)
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return Response({"error": f"Server Error: {str(e)}"}, status=500)
'''

if re.search(pattern, v_content, flags=re.DOTALL):
    v_content = re.sub(pattern, new_checkout_view.strip(), v_content, flags=re.DOTALL)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Patched sales/views.py checkout view.")
else:
    print("⚠️ Could not find exact checkout view. Attempting manual slicing.")
    start_idx = v_content.find("def checkout(request):")
    if start_idx != -1:
        # Find the end of the function (next @api_view or end of file)
        next_idx = v_content.find("@api_view", start_idx)
        if next_idx == -1:
            next_idx = len(v_content)
        
        # Replace decorator and function
        dec_idx = v_content.rfind("@api_view", 0, start_idx)
        v_content = v_content[:dec_idx] + new_checkout_view.strip() + "\n\n" + v_content[next_idx:]
        views_path.write_text(v_content, encoding="utf-8")
        print("✅ Patched using manual slicing.")

print("\n🎉 Done! Restart the server.")