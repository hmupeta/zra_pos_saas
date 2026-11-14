import requests
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from sales.models import Invoice
from .models import ZRASubmission


def submit_to_zra(invoice):
    """Branch-aware ZRA VSDC submission."""
    branch = invoice.company
    url = f"{branch.zra_vsdc_url.rstrip('/')}/trnsSales/saveSales"
    items = [{
        "itemSeq": i + 1,
        "itemCd": item.product.barcode,
        "itemClsCd": item.zra_item_code or "5059690800",
        "itemNm": item.product.name,
        "pkgUnitCd": "NT", "pkg": 1, "qtyUnitCd": "U",
        "qty": float(item.quantity), "prc": float(item.unit_price),
        "splyAmt": float(item.total),
        "taxTyCd": "A", "taxblAmt": float(item.total),
        "taxAmt": float(item.tax_amount),
        "totAmt": float(item.total + item.tax_amount),
    } for i, item in enumerate(invoice.items.all())]
    payload = {
        "tpin": branch.tpin, "bhfId": branch.branch_code,
        "dvcSrlNo": branch.zra_device_serial,
        "invcNo": invoice.invoice_number,
        "salesTyCd": "N", "rcptTyCd": "S", "pmtTyCd": "01", "salesSttsCd": "02",
        "cfmDt": invoice.created_at.strftime("%Y%m%d%H%M%S"),
        "salesDt": invoice.created_at.strftime("%Y%m%d"),
        "items": items,
        "totTaxblAmt": float(invoice.subtotal),
        "totTaxAmt": float(invoice.tax_total),
        "totAmt": float(invoice.total),
    }
    try:
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        return {"error": str(e)}


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def submit_invoice(request):
    invoice_id = request.data.get("invoice_id")
    try:
        invoice = Invoice.objects.get(pk=invoice_id, tenant=request.tenant)
    except Invoice.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
    result = submit_to_zra(invoice)
    submission = ZRASubmission.objects.create(
        invoice=invoice,
        status="SUCCESS" if result.get("resultCd") == "000" else "FAILED",
        response_data=result,
        validation_code=result.get("data", {}).get("validationCode", ""),
    )
    if submission.status == "SUCCESS":
        invoice.zra_validation_code = submission.validation_code
        invoice.save()
    return Response({"success": submission.status == "SUCCESS", "response": result})
