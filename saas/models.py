from django.db import models
from django.utils import timezone


class SignupApplication(models.Model):
    """
    Public signup request from a new business.
    Requires platform admin approval before Tenant is created.
    """
    STATUS = [
        ("PENDING", "Pending Review"),
        ("APPROVED", "Approved"),
        ("REJECTED", "Rejected"),
        ("INFO_REQUIRED", "Information Required"),
    ]

    # Applicant info
    business_name = models.CharField(max_length=200)
    business_type = models.CharField(max_length=50, blank=True)
    contact_name = models.CharField(max_length=200)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=30)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=50, default="Zambia")
    tpin = models.CharField(max_length=20, blank=True)

    # Selected plan
    plan = models.ForeignKey("core.SubscriptionPlan", on_delete=models.SET_NULL, null=True, blank=True)
    requested_branch_count = models.IntegerField(default=1)

    # Application status
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    notes = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)
    additional_info_requested = models.TextField(blank=True)

    # Approval
    reviewed_by = models.ForeignKey(
        "core.User", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="reviewed_applications",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)

    # Provisioned tenant
    provisioned_tenant = models.OneToOneField(
        "core.Tenant", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="signup_application",
    )
    admin_username = models.CharField(max_length=150, blank=True)

    submitted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.business_name} ({self.status})"


class TenantInvite(models.Model):
    """Invitation for a new user to join an existing tenant."""
    STATUS = [
        ("PENDING", "Pending"),
        ("ACCEPTED", "Accepted"),
        ("EXPIRED", "Expired"),
        ("REVOKED", "Revoked"),
    ]

    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE, related_name="invites")
    email = models.EmailField()
    full_name = models.CharField(max_length=200, blank=True)
    user_type = models.CharField(max_length=20, default="CASHIER")
    company = models.ForeignKey(
        "core.Company", on_delete=models.SET_NULL, null=True, blank=True,
        related_name="invites",
    )

    invite_token = models.CharField(max_length=100, unique=True)
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    invited_by = models.ForeignKey("core.User", on_delete=models.CASCADE, related_name="sent_invites")

    expires_at = models.DateTimeField()
    accepted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def is_valid(self):
        return self.status == "PENDING" and self.expires_at > timezone.now()

    def __str__(self):
        return f"Invite {self.email} → {self.tenant.name}"


class PlatformGatewayConfig(models.Model):
    PROVIDERS = [("MTN", "MTN MoMo"), ("STRIPE", "Stripe"), ("PAYPAL", "PayPal")]
    provider = models.CharField(max_length=20, choices=PROVIDERS, unique=True)
    is_enabled = models.BooleanField(default=False)
    
    # MTN Fields
    mtn_subscription_key = models.CharField(max_length=200, blank=True)
    mtn_api_user = models.CharField(max_length=200, blank=True)
    mtn_api_key = models.CharField(max_length=200, blank=True)
    mtn_target_env = models.CharField(max_length=50, default="sandbox")
    
    # Stripe/PayPal Fields
    api_key = models.CharField(max_length=200, blank=True)
    secret_key = models.CharField(max_length=200, blank=True)
    
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"SaaS Config: {self.provider}"


class TenantInvoice(models.Model):
    """Invoices sent by the SaaS platform to a tenant."""
    STATUS = [
        ("DRAFT", "Draft"),
        ("SENT", "Sent"),
        ("PAID", "Paid"),
        ("OVERDUE", "Overdue"),
        ("VOID", "Void"),
    ]

    tenant = models.ForeignKey("core.Tenant", on_delete=models.PROTECT, related_name="platform_invoices")
    invoice_number = models.CharField(max_length=50, unique=True)
    invoice_date = models.DateField()
    due_date = models.DateField()
    description = models.CharField(max_length=255, blank=True)
    subtotal = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    tax_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    total = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    amount_paid = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=STATUS, default="DRAFT")
    created_at = models.DateTimeField(auto_now_add=True)
    paid_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-invoice_date"]

    def __str__(self):
        return f"{self.invoice_number} · {self.tenant.name}"

class TenantPayment(models.Model):
    """Payments received from tenants."""
    METHODS = [
        ("BANK", "Bank Transfer"),
        ("CASH", "Cash"),
        ("CARD", "Card"),
        ("MOMO", "Mobile Money"),
    ]

    tenant = models.ForeignKey("core.Tenant", on_delete=models.PROTECT, related_name="platform_payments")
    invoice = models.ForeignKey(TenantInvoice, on_delete=models.SET_NULL, null=True, blank=True, related_name="payments")
    payment_number = models.CharField(max_length=50, unique=True)
    payment_date = models.DateField()
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=METHODS)
    reference = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-payment_date"]

    def __str__(self):
        return f"{self.payment_number} · {self.tenant.name} · K{self.amount}"
