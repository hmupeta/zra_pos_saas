from django.db import models
from django.conf import settings
from django.utils import timezone
from decimal import Decimal

class Supplier(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    tpin = models.CharField(max_length=20, blank=True)
    opening_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = [("tenant", "code")]

    def __str__(self):
        return self.name

    def current_balance(self):
        from django.db.models import Sum
        invs = self.invoices.aggregate(t=Sum('total'))['t'] or 0
        pays = self.payments.aggregate(t=Sum('amount'))['t'] or 0
        return self.opening_balance + invs - pays

class PurchaseOrder(models.Model):
    STATUS = [("DRAFT", "Draft"), ("RECEIVED", "Received"), ("CANCELLED", "Cancelled")]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="purchase_orders")
    po_number = models.CharField(max_length=50, unique=True)
    order_date = models.DateField(default=timezone.now)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    def __str__(self):
        return self.po_number

class SupplierInvoice(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="invoices")
    invoice_number = models.CharField(max_length=50)
    date = models.DateField(default=timezone.now)
    due_date = models.DateField(null=True, blank=True)
    total = models.DecimalField(max_digits=12, decimal_places=2)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, default="UNPAID")

    class Meta:
        unique_together = [("tenant", "invoice_number")]

class SupplierPayment(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    supplier = models.ForeignKey(Supplier, on_delete=models.PROTECT, related_name="payments")
    invoice = models.ForeignKey(SupplierInvoice, on_delete=models.SET_NULL, null=True, blank=True)
    payment_date = models.DateField(default=timezone.now)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    method = models.CharField(max_length=50, default="BANK")
    reference = models.CharField(max_length=100, blank=True)

class PurchaseOrderItem(models.Model):
    po = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2)
