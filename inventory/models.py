from django.db import models
from django.conf import settings
from decimal import Decimal


class TaxRate(models.Model):
    TYPES = [("STANDARD", "Standard 16%"), ("ZERO", "Zero"), ("EXEMPT", "Exempt")]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=50)
    tax_type = models.CharField(max_length=20, choices=TYPES, default="STANDARD")
    rate = models.DecimalField(max_digits=5, decimal_places=2, default=16)
    zra_tax_code = models.CharField(max_length=20, default="A")

    def __str__(self):
        return f"{self.name} ({self.rate}%)"


class Category(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE, null=True, blank=True)
    name = models.CharField(max_length=100)
    zra_item_code = models.CharField(max_length=50, blank=True, default="5059690800")
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Product(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE, related_name="products")
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE, related_name="products")
    barcode = models.CharField(max_length=50)
    name = models.CharField(max_length=200)
    image = models.ImageField(upload_to='products/', null=True, blank=True)
    category = models.ForeignKey(Category, on_delete=models.PROTECT)
    tax_rate = models.ForeignKey(TaxRate, on_delete=models.PROTECT)
    unit_cost = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    selling_price = models.DecimalField(max_digits=10, decimal_places=2)
    discount_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=0, help_text='Auto-applied discount %')
    
    current_stock = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    reorder_level = models.DecimalField(max_digits=10, decimal_places=2, default=10)
    zra_item_code = models.CharField(max_length=50, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("tenant", "barcode")]

    def __str__(self):
        return f"{self.barcode} - {self.name}"

    @property
    def tax_amount(self):
        return self.selling_price * self.tax_rate.rate / Decimal("100")


class StockMovement(models.Model):
    TYPES = [("IN", "In"), ("OUT", "Out"), ("ADJUST", "Adjust")]
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="movements")
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
    movement_type = models.CharField(max_length=10, choices=TYPES)
    reference = models.CharField(max_length=100, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True)
    created_at = models.DateTimeField(auto_now_add=True)


class StockTake(models.Model):
    STATUS = [
        ("DRAFT", "Draft (Counting)"),
        ("PENDING", "Pending Manager Approval"),
        ("COMPLETED", "Completed"),
        ("CANCELLED", "Cancelled"),
    ]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    reference = models.CharField(max_length=50)
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    counted_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="stocktakes_counted")
    approved_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="stocktakes_approved")
    created_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return self.reference

class StockTakeItem(models.Model):
    stocktake = models.ForeignKey(StockTake, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    system_qty = models.DecimalField(max_digits=10, decimal_places=2)
    counted_qty = models.DecimalField(max_digits=10, decimal_places=2)
    variance = models.DecimalField(max_digits=10, decimal_places=2) # counted - system

    def save(self, *args, **kwargs):
        self.variance = self.counted_qty - self.system_qty
        super().save(*args, **kwargs)


class StockTransfer(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    transfer_number = models.CharField(max_length=50, unique=True)
    from_company = models.ForeignKey("core.Company", on_delete=models.PROTECT, related_name="transfers_out")
    to_company = models.ForeignKey("core.Company", on_delete=models.PROTECT, related_name="transfers_in")
    status = models.CharField(max_length=20, default="COMPLETED") # DRAFT, COMPLETED
    created_by = models.ForeignKey("core.User", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.transfer_number

class StockTransferItem(models.Model):
    transfer = models.ForeignKey(StockTransfer, on_delete=models.CASCADE, related_name="items")
    product = models.ForeignKey(Product, on_delete=models.PROTECT)
    quantity = models.DecimalField(max_digits=10, decimal_places=2)
