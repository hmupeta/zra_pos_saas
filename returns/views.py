from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from decimal import Decimal
from django.utils import timezone
import datetime
from sales.models import Invoice, InvoiceItem
from inventory.models import Product, StockMovement
from inventory.services import BarcodeService
from accounting.models import Account, Journal, JournalLine
from .models import ReturnRequest, ReturnItem

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def search_invoice(request):
    query = request.query_params.get("q", "")
    if not query:
        return Response([])
    
    qs = Invoice.objects.filter(tenant=request.tenant, status="PAID").filter(
        invoice_number__icontains=query
    )[:5]
    
    return Response([{
        "id": i.id, "invoice_number": i.invoice_number,
        "date": i.created_at.strftime("%Y-%m-%d"),
        "total": float(i.total), "customer": i.customer_name
    } for i in qs])

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def invoice_details(request, pk):
    try:
        inv = Invoice.objects.get(pk=pk, tenant=request.tenant)
    except Invoice.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
        
    return Response({
        "id": inv.id, "invoice_number": inv.invoice_number,
        "items": [{
            "id": i.id, "name": i.product.name, "barcode": i.product.barcode,
            "qty_sold": float(i.quantity), "price": float(i.unit_price),
            "tax_rate": float(i.tax_rate), "total": float(i.total)
        } for i in inv.items.all()]
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def process_return(request):
    data = request.data
    invoice_id = data.get("invoice_id")
    items_data = data.get("items", [])
    
    try:
        invoice = Invoice.objects.get(pk=invoice_id, tenant=request.tenant)
    except Invoice.DoesNotExist:
        return Response({"error": "Invoice not found"}, status=404)

    if not items_data:
        return Response({"error": "No items selected for return"}, status=400)

    # Generate Return Number
    ref = f"RTN-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
    total_refund = Decimal("0")

    ret = ReturnRequest.objects.create(
        tenant=request.tenant, company=request.branch,
        invoice=invoice, return_number=ref, refund_method=data.get("refund_method", "CASH"),
        processed_by=request.user
    )

    for item in items_data:
        inv_item = InvoiceItem.objects.get(pk=item["invoice_item_id"])
        qty = Decimal(str(item["quantity"]))
        refund_amount = qty * inv_item.unit_price
        total_refund += refund_amount
        
        restock = item.get("restock", True)

        # 1. Create Return Item
        ReturnItem.objects.create(
            return_request=ret, invoice_item=inv_item, product=inv_item.product,
            quantity_returned=qty, refund_amount=refund_amount, restock=restock
        )

        # 2. Restock Inventory (if required)
        if restock:
            product = Product.objects.select_for_update().get(pk=inv_item.product.id)
            product.current_stock += qty
            product.save()
            
            StockMovement.objects.create(
                product=product, quantity=qty, movement_type="IN",
                reference=ref, notes="Customer Return", created_by=request.user
            )
            BarcodeService.invalidate_product(product)

    ret.total_refund = total_refund
    ret.save()

    # 3. Reverse Accounting
    # Dr Sales Returns (4010), Dr VAT Payable (2100), Cr Cash (1000)
    sales_returns = Account.objects.filter(tenant=request.tenant, code="4010").first()
    vat_account = Account.objects.filter(tenant=request.tenant, code="2100").first()
    cash_account = Account.objects.filter(tenant=request.tenant, code="1000").first()

    if sales_returns and vat_account and cash_account:
        # Calculate VAT portion (16% inclusive)
        net_amount = total_refund / Decimal("1.16")
        tax_amount = total_refund - net_amount

        journal = Journal.objects.create(
            tenant=request.tenant, company=request.branch,
            journal_number=f"REF-{ref}", date=timezone.now().date(),
            description=f"Refund for {invoice.invoice_number}",
            journal_type="ADJUSTMENT", status="POSTED", created_by=request.user
        )
        
        # Dr Sales Returns (Contra-Revenue)
        JournalLine.objects.create(journal=journal, account=sales_returns, debit=net_amount, description=f"Return {ref}")
        # Dr VAT Payable (we get VAT back from ZRA)
        JournalLine.objects.create(journal=journal, account=vat_account, debit=tax_amount, description=f"VAT Reversal {ref}")
        # Cr Cash (we paid out cash)
        JournalLine.objects.create(journal=journal, account=cash_account, credit=total_refund, description=f"Refund Payout {ref}")

    return Response({
        "success": True, "return_number": ref, "total_refund": float(total_refund)
    })