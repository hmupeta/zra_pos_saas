from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from datetime import datetime
from django.utils import timezone
from .models import Supplier, PurchaseOrder, SupplierInvoice, SupplierPayment
from inventory.models import Product, StockMovement
from accounting.models import Account, Journal, JournalLine

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def suppliers_list(request):
    if request.method == "GET":
        suppliers = Supplier.objects.filter(tenant=request.tenant, is_active=True)
        return Response([{
            "id": s.id, "name": s.name, "phone": s.phone, "balance": float(s.current_balance())
        } for s in suppliers])
        
    data = request.data
    import uuid
    s = Supplier.objects.create(
        tenant=request.tenant, code=f"SUP-{uuid.uuid4().hex[:4].upper()}",
        name=data.get("name"), phone=data.get("phone", ""), email=data.get("email", ""),
        opening_balance=Decimal(str(data.get("opening_balance", 0)))
    )
    return Response({"success": True, "id": s.id})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_invoice(request):
    """Record a supplier invoice and post to accounting"""
    data = request.data
    supplier = Supplier.objects.get(pk=data["supplier_id"], tenant=request.tenant)
    total = Decimal(str(data["total"]))
    
    invoice = SupplierInvoice.objects.create(
        tenant=request.tenant, supplier=supplier,
        invoice_number=data["invoice_number"], total=total
    )

    # Auto-Post to Accounting: Dr Inventory (1200), Cr Accounts Payable (2000)
    inv_account = Account.objects.filter(tenant=request.tenant, code="1200").first()
    ap_account = Account.objects.filter(tenant=request.tenant, code="2000").first()

    if inv_account and ap_account:
        journal = Journal.objects.create(
            tenant=request.tenant, company=request.branch,
            journal_number=f"PINV-{invoice.invoice_number}", date=timezone.now().date(),
            description=f"Supplier Invoice {invoice.invoice_number} - {supplier.name}",
            journal_type="PURCHASE", status="POSTED", created_by=request.user
        )
        JournalLine.objects.create(journal=journal, account=inv_account, debit=total, description="Stock Purchase")
        JournalLine.objects.create(journal=journal, account=ap_account, credit=total, description=f"Owed to {supplier.name}")

    return Response({"success": True, "id": invoice.id})

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def pay_supplier(request):
    """Record payment to supplier and post to accounting"""
    data = request.data
    supplier = Supplier.objects.get(pk=data["supplier_id"], tenant=request.tenant)
    amount = Decimal(str(data["amount"]))
    invoice_id = data.get("invoice_id")

    invoice = None
    if invoice_id:
        invoice = SupplierInvoice.objects.get(pk=invoice_id, tenant=request.tenant)
        invoice.amount_paid += amount
        invoice.status = "PAID" if invoice.amount_paid >= invoice.total else "PARTIAL"
        invoice.save()

    payment = SupplierPayment.objects.create(
        tenant=request.tenant, supplier=supplier, invoice=invoice,
        amount=amount, method=data.get("method", "BANK"), reference=data.get("reference", "")
    )

    # Auto-Post to Accounting: Dr Accounts Payable (2000), Cr Cash/Bank (1000/1010)
    ap_account = Account.objects.filter(tenant=request.tenant, code="2000").first()
    bank_account = Account.objects.filter(tenant=request.tenant, code="1010").first() # Default to bank

    if ap_account and bank_account:
        journal = Journal.objects.create(
            tenant=request.tenant, company=request.branch,
            journal_number=f"PAY-{payment.id}", date=timezone.now().date(),
            description=f"Payment to {supplier.name}",
            journal_type="PURCHASE", status="POSTED", created_by=request.user
        )
        JournalLine.objects.create(journal=journal, account=ap_account, debit=amount, description="Reduce AP")
        JournalLine.objects.create(journal=journal, account=bank_account, credit=amount, description="Cash Out")

    return Response({"success": True})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def supplier_invoices(request):
    qs = SupplierInvoice.objects.filter(tenant=request.tenant).order_by("-date")
    return Response([{
        "id": i.id, "supplier": i.supplier.name, "invoice_number": i.invoice_number,
        "date": i.date.strftime("%Y-%m-%d"), "total": float(i.total),
        "paid": float(i.amount_paid), "status": i.status
    } for i in qs])


from django.utils import timezone
from .models import PurchaseOrder, PurchaseOrderItem

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def purchase_orders_list(request):
    if request.method == "GET":
        qs = PurchaseOrder.objects.filter(tenant=request.tenant).order_by("-order_date")
        return Response([{
            "id": po.id, "po_number": po.po_number, "supplier": po.supplier.name,
            "date": po.order_date.strftime("%Y-%m-%d"), "total": float(po.total),
            "status": po.status
        } for po in qs])

    # Create New PO
    data = request.data
    items = data.get("items", [])
    if not items:
        return Response({"error": "PO must have items"}, status=400)

    import datetime
    po_num = f"PO-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
    
    po = PurchaseOrder.objects.create(
        tenant=request.tenant, company=request.branch,
        supplier_id=data["supplier_id"], po_number=po_num,
        created_by=request.user
    )

    total = Decimal("0")
    for item in items:
        qty = Decimal(str(item["quantity"]))
        cost = Decimal(str(item["unit_cost"]))
        total += (qty * cost)
        PurchaseOrderItem.objects.create(
            po=po, product_id=item["product_id"],
            quantity=qty, unit_cost=cost
        )

    po.total = total
    po.save()

    return Response({"success": True, "id": po.id, "po_number": po.po_number})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def po_details(request, pk):
    try:
        po = PurchaseOrder.objects.get(pk=pk, tenant=request.tenant)
    except PurchaseOrder.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
        
    return Response({
        "id": po.id, "po_number": po.po_number, "supplier": po.supplier.name,
        "status": po.status, "total": float(po.total),
        "items": [{
            "id": i.id, "product_id": i.product_id, "product": i.product.name,
            "quantity": float(i.quantity), "unit_cost": float(i.unit_cost)
        } for i in po.items.all()]
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def receive_po(request, pk):
    """Marks PO as RECEIVED and adds inventory."""
    try:
        po = PurchaseOrder.objects.get(pk=pk, tenant=request.tenant, status="DRAFT")
    except PurchaseOrder.DoesNotExist:
        return Response({"error": "PO not found or already received"}, status=400)

    for item in po.items.all():
        product = item.product
        product.current_stock += item.quantity
        product.save()

    po.status = "RECEIVED"
    po.save()
    return Response({"success": True})
