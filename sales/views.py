from inventory.models import Product
from decimal import Decimal
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

# --- FIXED IMPORTS ---
from .models import (
    StockReservation, StockReservationItem, Shift, 
    Invoice, InvoiceItem, Quotation, QuotationItem, SalesTarget
)

from .cart_service import CartService
from .receipt_service import ReceiptService
from inventory.services import BarcodeService
from core.isolation import branch_filter, assert_access
from django.db.models import Sum, Count


def get_safe_tenant_branch(request):
    """Fallback helper to get tenant and branch even if middleware fails."""
    branch = getattr(request, 'branch', None)
    if not branch:
        from core.models import BranchAccess
        access = BranchAccess.objects.filter(user=request.user).first()
        branch = access.company if access else None

    tenant = getattr(request, 'tenant', None)
    if not tenant:
        tenant = request.user.tenant
    if not tenant and branch:
        tenant = branch.tenant

    return tenant, branch


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def open_shift(request):
    if Shift.objects.filter(cashier=request.user, is_closed=False).exists():
        return Response({"error": "Shift already open"}, status=400)

    tenant, branch = get_safe_tenant_branch(request)
    if not branch:
        return Response({"error": "No branch assigned to your account. Contact your manager."}, status=403)
    if not tenant:
        return Response({"error": "No tenant assigned to your account."}, status=403)

    shift = Shift.objects.create(
        tenant=tenant,
        company=branch, 
        cashier=request.user,
        opening_balance=request.data.get("opening_balance", 0),
    )
    return Response({"shift_id": shift.id, "message": "Shift opened"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def current_shift(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=404)
    return Response({"id": shift.id, "opening_balance": float(shift.opening_balance)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def scan_add(request):
    barcode = request.data.get("barcode")
    try:
        quantity = int(request.data.get("quantity", 1))
    except ValueError:
        quantity = 1

    tenant, branch = get_safe_tenant_branch(request)
    if not branch:
        return Response({"error": "No branch assigned to your account."}, status=403)
    if not tenant:
        return Response({"error": "No tenant assigned to your account."}, status=403)

    # 1. Look up the product
    product = BarcodeService.lookup(tenant.id, branch.id, barcode)
    if not product:
        return Response({"error": "Product not found"}, status=404)

    # 2. Get the current open shift
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=400)

    # 3. Use CartService to add the item
    try:
        cart = CartService.add_item(tenant.id, branch.id, shift.id, product, quantity)
    except AttributeError:
        # Fallback if add_item doesn't exist
        cart = CartService.get(tenant.id, branch.id, shift.id)
        items = cart.get("items", [])
        
        found = False
        for item in items:
            if item["product_id"] == product["id"] if isinstance(product, dict) else item["product_id"] == product.id:
                item["quantity"] += quantity
                found = True
                break
        
        if not found:
            items.append({
                "product_id": product["id"] if isinstance(product, dict) else product.id,
                "barcode": product["barcode"] if isinstance(product, dict) else product.barcode,
                "name": product["name"] if isinstance(product, dict) else product.name,
                "quantity": quantity,
                "unit_price": float(product["selling_price"] if isinstance(product, dict) else product.selling_price),
                "tax_rate": float(product["tax_rate"] if isinstance(product, dict) else (product.tax_rate.rate if product.tax_rate else 0))
            })
            
        cart["items"] = items
        CartService.save(tenant.id, branch.id, shift.id, cart)

    # 4. Recalculate totals
    totals = CartService.totals(cart)

    # 6. Return the updated cart
    return Response({
        "product": {
            "id": product["id"] if isinstance(product, dict) else product.id,
            "name": product["name"] if isinstance(product, dict) else product.name,
            "barcode": product["barcode"] if isinstance(product, dict) else product.barcode,
            "selling_price": float(product["selling_price"] if isinstance(product, dict) else product.selling_price),
        },
        "cart": {**cart, "totals": totals},
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_cart(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=404)
    
    tenant, branch = get_safe_tenant_branch(request)
    if not tenant or not branch:
        return Response({"error": "No tenant/branch assigned"}, status=403)
        
    cart = CartService.get(tenant.id, branch.id, shift.id)
    return Response({**cart, "totals": CartService.totals(cart)})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cart_clear(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No shift"}, status=400)
    
    tenant, branch = get_safe_tenant_branch(request)
    if not tenant or not branch:
        return Response({"error": "No tenant/branch assigned"}, status=403)
        
    CartService.clear(tenant.id, branch.id, shift.id)
    return Response({"success": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def checkout(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=400)
        
    payments = request.data.get("payments", [])
    if not payments:
        return Response({"error": "No payment details provided"}, status=400)

    tenant, branch = get_safe_tenant_branch(request)
    if not tenant or not branch:
        return Response({"error": "No tenant/branch assigned"}, status=403)

    try:
        invoice = CartService.checkout(
            tenant.id, branch.id, shift, request.user,
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


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def close_shift(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=404)
    shift.closing_time = timezone.now()
    shift.is_closed = True
    shift.save()
    return Response({"success": True, "message": "Shift closed"})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invoices_list(request):
    qs = branch_filter(request, Invoice.objects.all())
    return Response([{
        "id": i.id, "invoice_number": i.invoice_number,
        "total": float(i.total), "status": i.status,
        "created_at": i.created_at.isoformat(),
    } for i in qs[:100]])


# --- NEW VIEW: Invoice Detail ---
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invoice_detail(request, pk):
    try:
        invoice = Invoice.objects.prefetch_related('items__product').get(pk=pk, tenant=request.tenant)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    items = []
    for item in invoice.items.all():
        items.append({
            "id": item.id,
            "product_name": item.product.name,
            "quantity": float(item.quantity),
            "unit_price": float(item.unit_price),
            "tax_amount": float(item.tax_amount),
            "total": float(item.total),
        })

    return Response({
        "id": invoice.id,
        "invoice_number": invoice.invoice_number,
        "created_at": invoice.created_at,
        "status": invoice.status,
        "payment_method": invoice.payment_method,
        "customer_name": invoice.customer_name,
        "subtotal": float(invoice.subtotal),
        "tax_total": float(invoice.tax_total),
        "discount_total": float(invoice.discount_total),
        "total": float(invoice.total),
        "items": items,
    })


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def receipt_text(request, invoice_id):
    tenant, branch = get_safe_tenant_branch(request)
    if not tenant or not branch:
        return Response({"error": "No tenant/branch assigned"}, status=403)

    try:
        invoice = Invoice.objects.get(pk=invoice_id, tenant=tenant, company=branch)
    except Invoice.DoesNotExist:
        return Response({"error": "Not found"}, status=404)

    return Response({"text": ReceiptService(invoice).to_text()})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_cart_customer(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=400)
    
    customer_name = request.data.get("customer_name", "Cash Customer").strip()
    if not customer_name:
        customer_name = "Cash Customer"
        
    tenant, branch = get_safe_tenant_branch(request)
    if not tenant or not branch:
        return Response({"error": "No tenant/branch assigned"}, status=403)

    cart = CartService.get(tenant.id, branch.id, shift.id)
    cart["customer_name"] = customer_name
    CartService.save(tenant.id, branch.id, shift.id, cart)
    
    return Response({"success": True, "customer_name": customer_name})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def void_invoice(request):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER", "SALES_ADMIN"):
        return Response({"error": "Only Managers or Sales Admins can void sales"}, status=403)
    invoice_id = request.data.get("invoice_id")
    try:
        invoice = Invoice.objects.get(pk=invoice_id, tenant=request.tenant)
        invoice.status = "VOID"
        invoice.save()
        return Response({"success": True})
    except Invoice.DoesNotExist:
        return Response({"error": "Not found"}, status=404)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def apply_cart_discount(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=400)
    
    discount_amount = float(request.data.get("discount_amount", 0))
    if discount_amount < 0:
        return Response({"error": "Invalid discount amount"}, status=400)

    # RBAC: Discounts over 100 require Manager/Owner
    if discount_amount > 100 and request.user.user_type not in ("TENANT_OWNER", "MANAGER", "SALES_ADMIN"):
        return Response({"error": "Discounts over K100 require Manager approval"}, status=403)

    tenant, branch = get_safe_tenant_branch(request)
    if not tenant or not branch:
        return Response({"error": "No tenant/branch assigned"}, status=403)

    cart = CartService.apply_discount(tenant.id, branch.id, shift.id, discount_amount)
    return Response({"success": True, "cart": {**cart, "totals": CartService.totals(cart)}})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shifts_list(request):
    """List all shifts for this branch, recalculating math dynamically."""
    tenant, branch = get_safe_tenant_branch(request)
    if not tenant or not branch:
        return Response({"error": "No tenant/branch assigned"}, status=403)

    qs = Shift.objects.filter(tenant=tenant, company=branch).prefetch_related('invoices').order_by("-opening_time")
    
    data = []
    for s in qs[:100]:
        invoices = s.invoices.filter(status="PAID")
        
        # Calculate breakdown
        total_sales = sum(inv.total for inv in invoices)
        cash_sales = sum(inv.total for inv in invoices if inv.payment_method == "CASH")
        momo_sales = sum(inv.total for inv in invoices if inv.payment_method in ("MOMO", "MTN", "AIRTEL", "ZAMTEL"))
        
        expected_cash = s.opening_balance + cash_sales
        saved_actual = getattr(s, 'actual_cash', 0) or 0
        recalculated_variance = saved_actual - expected_cash
        
        data.append({
            "id": s.id,
            "cashier": s.cashier.username,
            "opening_time": s.opening_time.strftime("%Y-%m-%d %H:%M"),
            "closing_time": s.closing_time.strftime("%H:%M") if s.closing_time else "OPEN",
            "opening_balance": float(s.opening_balance),
            "total_sales": float(total_sales),
            "cash_sales": float(cash_sales),
            "momo_sales": float(momo_sales),
            "expected_cash": float(expected_cash),
            "actual_cash": float(saved_actual),
            "variance": float(recalculated_variance),
            "is_closed": s.is_closed
        })
    return Response(data)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shift_details(request, pk):
    """Get details of a specific shift, including all its sales."""
    tenant, branch = get_safe_tenant_branch(request)
    if not tenant:
        return Response({"error": "No tenant assigned"}, status=403)

    try:
        shift = Shift.objects.get(pk=pk, tenant=tenant)
    except Shift.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
        
    invoices = shift.invoices.filter(status="PAID")
    
    # Recalculate expected cash
    total_sales = sum(inv.total for inv in invoices)
    cash_sales = sum(inv.total for inv in invoices if inv.payment_method == "CASH")
    momo_sales = sum(inv.total for inv in invoices if inv.payment_method in ("MOMO", "MTN", "AIRTEL", "ZAMTEL"))
    card_sales = sum(inv.total for inv in invoices if inv.payment_method == "CARD")
    
    expected_cash = shift.opening_balance + cash_sales
    saved_actual = getattr(shift, 'actual_cash', 0) or 0
    recalculated_variance = saved_actual - expected_cash
    
    return Response({
        "shift": {
            "id": shift.id,
            "cashier": shift.cashier.username,
            "opening_time": shift.opening_time.strftime("%Y-%m-%d %H:%M"),
            "closing_time": shift.closing_time.strftime("%Y-%m-%d %H:%M") if shift.closing_time else None,
            "opening_balance": float(shift.opening_balance),
            "expected_cash": float(expected_cash), 
            "actual_cash": float(saved_actual),
            "variance": float(recalculated_variance),
            "total_sales": float(total_sales),
            "cash_sales": float(cash_sales),
            "momo_sales": float(momo_sales),
            "card_sales": float(card_sales),
        },
        "sales": [{
            "invoice_number": i.invoice_number,
            "time": i.created_at.strftime("%H:%M"),
            "customer": i.customer_name,
            "total": float(i.total),
            "payment_method": i.payment_method
        } for i in invoices]
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def agent_targets(request):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)
        
    now = timezone.now()
    
    if request.method == "GET":
        month = int(request.query_params.get("month", now.month))
        year = int(request.query_params.get("year", now.year))
        
        # Get all sales agents in this tenant
        agents = request.tenant.users.filter(user_type="SALES_AGENT", is_active=True)
        
        data = []
        for agent in agents:
            # 1. Get target
            target = SalesTarget.objects.filter(tenant=request.tenant, agent=agent, month=month, year=year).first()
            target_amt = float(target.target_amount) if target else 0
            comm_rate = float(target.commission_rate) if target else 2.0
            
            # 2. Calculate actual sales for this month
            invoices = Invoice.objects.filter(
                tenant=request.tenant, cashier=agent, status="PAID",
                created_at__year=year, created_at__month=month
            )
            actual_sales = float(invoices.aggregate(t=Sum("total"))["t"] or 0)
            
            # 3. Calculate commission
            commission_earned = actual_sales * (comm_rate / 100)
            
            # 4. Calculate progress %
            progress = (actual_sales / target_amt * 100) if target_amt > 0 else 0

            data.append({
                "agent_id": agent.id,
                "agent_name": agent.username,
                "month": month,
                "year": year,
                "target_amount": target_amt,
                "actual_sales": actual_sales,
                "commission_rate": comm_rate,
                "commission_earned": commission_earned,
                "progress": min(round(progress, 1), 100)
            })
            
        return Response(data)
        
    elif request.method == "POST":
        # Set/Update Target
        data = request.data
        agent_id = data.get("agent_id")
        month = data.get("month")
        year = data.get("year")
        target_amount = data.get("target_amount")
        commission_rate = data.get("commission_rate")
        
        target, created = SalesTarget.objects.update_or_create(
            tenant=request.tenant, agent_id=agent_id, month=month, year=year,
            defaults={"target_amount": target_amount, "commission_rate": commission_rate}
        )
        return Response({"success": True})


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def shift_summary(request):
    """Generate the Z-Report data for the current active shift."""
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=404)

    invoices = shift.invoices.filter(status="PAID")
    
    # Calculate totals
    total_sales = sum(inv.total for inv in invoices)
    cash_sales = sum(inv.total for inv in invoices if inv.payment_method == "CASH")
    momo_sales = sum(inv.total for inv in invoices if inv.payment_method in ("MOMO", "MTN", "AIRTEL", "ZAMTEL"))
    card_sales = sum(inv.total for inv in invoices if inv.payment_method == "CARD")
    
    # Expected cash = Opening Balance + Cash Sales
    expected_cash = shift.opening_balance + cash_sales

    return Response({
        "shift_id": shift.id,
        "opening_time": shift.opening_time.strftime("%Y-%m-%d %H:%M"),
        "opening_balance": float(shift.opening_balance),
        "total_sales": float(total_sales),
        "transaction_count": invoices.count(),
        "cash_sales": float(cash_sales),
        "momo_sales": float(momo_sales),
        "card_sales": float(card_sales),
        "expected_cash": float(expected_cash),
    })


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def reconcile_shift(request, pk):
    """Allows managers to retroactively fix the cash count for a closed shift."""
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER", "ADMIN"):
        return Response({"error": "Insufficient permissions"}, status=403)

    try:
        shift = Shift.objects.get(pk=pk, tenant=request.tenant)
    except Shift.DoesNotExist:
        return Response({"error": "Shift not found"}, status=404)

    if not shift.is_closed:
        return Response({"error": "Cannot reconcile an active shift"}, status=400)

    actual_cash = Decimal(str(request.data.get("actual_cash", 0)))
    
    # Recalculate expected cash to ensure accuracy
    invoices = shift.invoices.filter(status="PAID")
    cash_sales = sum(inv.total for inv in invoices if inv.payment_method == "CASH")
    expected_cash = shift.opening_balance + cash_sales
    
    # Update shift
    shift.actual_cash = actual_cash
    shift.expected_amount = expected_cash
    shift.variance = actual_cash - expected_cash
    shift.save()

    return Response({
        "success": True, 
        "message": "Shift reconciled successfully",
        "new_variance": float(shift.variance)
    })


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def quotations_list(request):
    if request.method == "GET":
        qs = Quotation.objects.filter(tenant=request.tenant, company=request.branch).order_by("-created_at")
        return Response([{
            "id": q.id, "quotation_number": q.quotation_number, 
            "customer": q.customer_name, "date": q.created_at.strftime("%Y-%m-%d"),
            "total": float(q.total), "status": q.status
        } for q in qs[:100]])

    # POST: Create Quotation
    data = request.data
    items_data = data.get("items", [])
    if not items_data:
        return Response({"error": "Quotation must have items"}, status=400)

    import datetime
    q_num = f"QT-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

    total_subtotal = 0
    total_tax = 0
    
    quotation = Quotation.objects.create(
        tenant=request.tenant, company=request.branch,
        quotation_number=q_num, customer_id=data.get("customer_id"),
        customer_name=data.get("customer_name", "Walk-in Customer"),
        subtotal=0, tax_total=0, total=0,
        created_by=request.user,
        valid_until=data.get("valid_until")
    )

    for item in items_data:
        product = Product.objects.get(id=item["product_id"], tenant=request.tenant)
        qty = Decimal(str(item["quantity"]))
        price = product.selling_price
        line_total = qty * price
        line_tax = line_total * product.tax_rate.rate / 100
        
        total_subtotal += line_total
        total_tax += line_tax
        
        QuotationItem.objects.create(
            quotation=quotation, product=product, quantity=qty,
            unit_price=price, tax_rate=product.tax_rate.rate, total=line_total
        )

    quotation.subtotal = total_subtotal
    quotation.tax_total = total_tax
    quotation.total = total_subtotal + total_tax
    quotation.save()

    return Response({"success": True, "id": quotation.id, "quotation_number": q_num})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def convert_quotation(request, pk):
    """Converts a quotation into a paid Invoice and adjusts stock."""
    try:
        q = Quotation.objects.get(pk=pk, tenant=request.tenant, status="DRAFT")
    except Quotation.DoesNotExist:
        return Response({"error": "Quotation not found or already converted"}, status=404)

    # Create the Invoice
    import datetime
    inv_num = f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-CONV"
    
    # We need an open shift to attach the invoice to
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "You must open a shift before converting a quotation."}, status=400)

    invoice = Invoice.objects.create(
        invoice_number=inv_num, tenant=request.tenant, company=request.branch,
        shift=shift, cashier=request.user,
        customer_name=q.customer_name, customer_id=q.customer_id,
        subtotal=q.subtotal, tax_total=q.tax_total, total=q.total,
        status="PAID", payment_method="CASH"
    )

    for item in q.items.all():
        InvoiceItem.objects.create(
            invoice=invoice, product=item.product, quantity=item.quantity,
            unit_price=item.unit_price, tax_rate=item.tax_rate,
            tax_amount=(item.total * item.tax_rate / 100), total=item.total,
            zra_item_code=item.product.zra_item_code
        )
        # Deduct stock
        item.product.current_stock -= item.quantity
        item.product.save()

    q.status = "CONVERTED"
    q.converted_invoice = invoice
    q.save()

    return Response({"success": True, "invoice_id": invoice.id, "invoice_number": invoice.invoice_number})


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def reservations_list(request):
    if request.method == "GET":
        qs = StockReservation.objects.filter(tenant=request.tenant, company=request.branch).order_by("-created_at")
        return Response([{
            "id": r.id, "reservation_number": r.reservation_number, 
            "customer": r.customer_name, "phone": r.customer_phone,
            "date": r.created_at.strftime("%Y-%m-%d"),
            "valid_until": r.valid_until.strftime("%Y-%m-%d") if r.valid_until else "N/A",
            "total": float(r.total), "deposit": float(r.deposit_paid), "status": r.status
        } for r in qs[:100]])

    # POST: Create Reservation (Locks Stock)
    data = request.data
    items_data = data.get("items", [])
    if not items_data:
        return Response({"error": "Reservation must have items"}, status=400)

    import datetime
    res_num = f"RES-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"

    total_subtotal = Decimal("0")
    total_tax = Decimal("0")
    
    # 1. Validate Stock
    for item in items_data:
        product = Product.objects.get(id=item["product_id"], tenant=request.tenant)
        qty = Decimal(str(item["quantity"]))
        if product.current_stock < qty:
            return Response({"error": f"Not enough stock for {product.name}. Only {product.current_stock} left."}, status=400)

    # 2. Create Reservation
    reservation = StockReservation.objects.create(
        tenant=request.tenant, company=request.branch,
        reservation_number=res_num, 
        customer_id=data.get("customer_id"),
        customer_name=data.get("customer_name", "Walk-in Customer"),
        customer_phone=data.get("customer_phone", ""),
        subtotal=0, tax_total=0, total=0,
        deposit_paid=Decimal(str(data.get("deposit_paid", 0))),
        created_by=request.user,
        valid_until=data.get("valid_until"),
        notes=data.get("notes", "")
    )

    # 3. Create Items & LOCK STOCK
    for item in items_data:
        product = Product.objects.get(id=item["product_id"], tenant=request.tenant)
        qty = Decimal(str(item["quantity"]))
        price = product.selling_price
        line_total = qty * price
        line_tax = line_total * product.tax_rate.rate / 100
        
        total_subtotal += line_total
        total_tax += line_tax
        
        StockReservationItem.objects.create(
            reservation=reservation, product=product, quantity=qty,
            unit_price=price, tax_rate=product.tax_rate.rate, total=line_total
        )
        
        # DEDUCT STOCK IMMEDIATELY
        product.current_stock -= qty
        product.save()

    reservation.subtotal = total_subtotal
    reservation.tax_total = total_tax
    reservation.total = total_subtotal + total_tax
    reservation.save()

    return Response({"success": True, "id": reservation.id, "reservation_number": res_num})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def cancel_reservation(request, pk):
    """Cancels reservation and returns stock to the shelf."""
    try:
        r = StockReservation.objects.get(pk=pk, tenant=request.tenant, status="ACTIVE")
    except StockReservation.DoesNotExist:
        return Response({"error": "Reservation not found or already processed"}, status=404)

    # Return stock
    for item in r.items.all():
        product = item.product
        product.current_stock += item.quantity
        product.save()

    r.status = "CANCELLED"
    r.save()

    return Response({"success": True})


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def convert_reservation(request, pk):
    """Converts reservation to an invoice. Stock is already deducted."""
    try:
        r = StockReservation.objects.get(pk=pk, tenant=request.tenant, status="ACTIVE")
    except StockReservation.DoesNotExist:
        return Response({"error": "Reservation not found or already processed"}, status=404)

    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "You must open a shift to convert a reservation."}, status=400)

    import datetime
    inv_num = f"{datetime.datetime.now().strftime('%y%m%d%H%M%S')}-RES"
    
    invoice = Invoice.objects.create(
        invoice_number=inv_num, tenant=request.tenant, company=request.branch,
        shift=shift, cashier=request.user,
        customer_name=r.customer_name, customer_id=r.customer_id,
        subtotal=r.subtotal, tax_total=r.tax_total, total=r.total,
        status="PAID", payment_method="CASH"
    )

    for item in r.items.all():
        InvoiceItem.objects.create(
            invoice=invoice, product=item.product, quantity=item.quantity,
            unit_price=item.unit_price, tax_rate=item.tax_rate,
            tax_amount=(item.total * item.tax_rate / 100), total=item.total,
            zra_item_code=item.product.zra_item_code
        )

    r.status = "CONVERTED"
    r.converted_invoice = invoice
    r.save()

    return Response({"success": True, "invoice_id": invoice.id, "invoice_number": invoice.invoice_number})


@api_view(["GET", "PUT", "DELETE"])
@permission_classes([IsAuthenticated])
def quotation_detail(request, pk):
    try:
        q = Quotation.objects.get(pk=pk, tenant=request.tenant)
    except Quotation.DoesNotExist:
        return Response({"error": "Quotation not found"}, status=404)

    if request.method == "GET":
        return Response({
            "id": q.id,
            "quotation_number": q.quotation_number,
            "customer": q.customer_name,
            "customer_id": q.customer_id,
            "valid_until": q.valid_until.strftime("%Y-%m-%d") if q.valid_until else "",
            "status": q.status,
            "notes": q.notes,
            "items": [{
                "id": i.id,
                "product_id": i.product_id,
                "product_name": i.product.name,
                "quantity": float(i.quantity),
                "unit_price": float(i.unit_price),
                "total": float(i.total)
            } for i in q.items.all()]
        })

    elif request.method == "PUT":
        if q.status != "DRAFT":
            return Response({"error": "Only draft quotations can be edited"}, status=400)

        data = request.data
        items_data = data.get("items", [])
        if not items_data:
            return Response({"error": "Quotation must have items"}, status=400)

        total_subtotal = Decimal("0")
        total_tax = Decimal("0")

        # Clear existing items
        q.items.all().delete()

        for item in items_data:
            product = Product.objects.get(id=item["product_id"], tenant=request.tenant)
            qty = Decimal(str(item["quantity"]))
            price = product.selling_price
            line_total = qty * price
            line_tax = line_total * product.tax_rate.rate / 100

            total_subtotal += line_total
            total_tax += line_tax

            QuotationItem.objects.create(
                quotation=q, product=product, quantity=qty,
                unit_price=price, tax_rate=product.tax_rate.rate, total=line_total
            )

        q.customer_id = data.get("customer_id") or None
        q.customer_name = data.get("customer_name", "Walk-in Customer")
        q.valid_until = data.get("valid_until") or None
        q.subtotal = total_subtotal
        q.tax_total = total_tax
        q.total = total_subtotal + total_tax
        q.save()

        return Response({"success": True})

    elif request.method == "DELETE":
        if q.status != "DRAFT":
            return Response({"error": "Only draft quotations can be deleted"}, status=400)
        q.delete()
        return Response({"success": True})