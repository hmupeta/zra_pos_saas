from django.core.mail import send_mail
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from sales.models import Invoice
from sales.receipt_service import ReceiptService
from .models import NotificationLog


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def email_receipt(request):
    invoice_id = request.data.get("invoice_id")
    email = request.data.get("email")
    try:
        invoice = Invoice.objects.get(pk=invoice_id, tenant=request.tenant)
    except Invoice.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
    body = ReceiptService(invoice).to_text()
    log = NotificationLog.objects.create(
        tenant=request.tenant, channel="EMAIL", recipient=email,
        subject=f"Receipt {invoice.invoice_number}", message=body,
    )
    try:
        send_mail(log.subject, body, "noreply@yourstore.com", [email])
        log.status = "SENT"
    except Exception as e:
        log.status = "FAILED"
        log.error = str(e)
    log.save()
    return Response({"success": log.status == "SENT"})
