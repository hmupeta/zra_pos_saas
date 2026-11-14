from django.db import models
from django.conf import settings

class ReturnRequest(models.Model):
    STATUS = [
        ("PENDING", "Pending"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    invoice = models.ForeignKey("sales.Invoice", on_delete=models.PROTECT, related_name="returns")
    return_number = models.CharField(max_length=50, unique=True)
    reason = models.CharField(max_length=100, default="Customer Request")
    refund_method = models.CharField(max_length=50, default="CASH") # CASH, STORE_CREDIT
    total_refund = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="COMPLETED")
    processed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.return_number

class ReturnItem(models.Model):
    return_request = models.ForeignKey(ReturnRequest, on_delete=models.CASCADE, related_name="items")
    invoice_item = models.ForeignKey("sales.InvoiceItem", on_delete=models.PROTECT)
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    quantity_returned = models.DecimalField(max_digits=10, decimal_places=2)
    refund_amount = models.DecimalField(max_digits=12, decimal_places=2)
    restock = models.BooleanField(default=True)