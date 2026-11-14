from django.db import models
from django.conf import settings
from decimal import Decimal

class Account(models.Model):
    TYPES = [("ASSET", "Asset"), ("LIABILITY", "Liability"), ("EQUITY", "Equity"),
             ("REVENUE", "Revenue"), ("EXPENSE", "Expense")]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="accounts")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=TYPES)
    is_header = models.BooleanField(default=False)
    is_control = models.BooleanField(default=False)
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("tenant", "code")]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def normal_balance(self):
        if self.account_type in ("ASSET", "EXPENSE"):
            return "DEBIT"
        return "CREDIT"

    def balance(self):
        from django.db.models import Sum
        agg = self.journal_lines.aggregate(dr=Sum("debit"), cr=Sum("credit"))
        dr, cr = agg["dr"] or Decimal("0"), agg["cr"] or Decimal("0")
        
        # We return the balance according to its normal side (positive = normal, negative = abnormal)
        if self.normal_balance == "DEBIT":
            return self.opening_balance + dr - cr
        else:
            return self.opening_balance + cr - dr


class Journal(models.Model):
    TYPES = [("SALES", "Sales"), ("PURCHASE", "Purchase"), ("GENERAL", "General"),
             ("ADJUSTMENT", "Adjustment")]
    STATUS = [("DRAFT", "Draft"), ("POSTED", "Posted"), ("VOID", "Void")]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    journal_number = models.CharField(max_length=50)
    date = models.DateField()
    description = models.TextField()
    journal_type = models.CharField(max_length=20, choices=TYPES, default="GENERAL")
    status = models.CharField(max_length=20, choices=STATUS, default="POSTED")
    source_invoice = models.ForeignKey("sales.Invoice", on_delete=models.SET_NULL, null=True, blank=True, related_name="journals")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        unique_together = [("tenant", "journal_number")]

    def total_debit(self):
        from django.db.models import Sum
        return self.lines.aggregate(t=Sum("debit"))["t"] or Decimal("0")

    def total_credit(self):
        from django.db.models import Sum
        return self.lines.aggregate(t=Sum("credit"))["t"] or Decimal("0")

    def is_balanced(self):
        return self.total_debit() == self.total_credit()


class JournalLine(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        side = "DR" if self.debit > 0 else "CR"
        amount = self.debit if self.debit > 0 else self.credit
        return f"{side} {self.account.code} - {amount}"

class Expense(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    date = models.DateField()
    account = models.ForeignKey(Account, on_delete=models.PROTECT, help_text="Expense category (e.g. Rent, Utilities)")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, default="CASH")
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey("core.User", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account.name} - {self.amount}"
