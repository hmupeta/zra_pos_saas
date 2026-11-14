from django.db import models
from core.encryption import EncryptedCharField


class BranchPaymentConfig(models.Model):
    PROVIDERS = [
        ("MTN_DIRECT", "MTN Mobile Money"),
        ("AIRTEL_DIRECT", "Airtel Money"),
        ("ZAMTEL_DIRECT", "Zamtel Kwacha"),
        ("STRIPE", "Stripe (Card)"),
        ("PAYPAL", "PayPal"),
        ("MONEYUNIFY", "MoneyUnify (Aggregated)"),
    ]
    branch = models.ForeignKey("core.Company", on_delete=models.CASCADE, related_name="payment_configs")
    provider = models.CharField(max_length=20, choices=PROVIDERS)
    merchant_id = EncryptedCharField(blank=True)
    api_key = EncryptedCharField(blank=True)
    api_secret = EncryptedCharField(blank=True)
    is_default = models.BooleanField(default=False)
    is_enabled = models.BooleanField(default=True)
    extra_config = models.JSONField(default=dict, blank=True)
    mtn_subscription_key = EncryptedCharField(blank=True)
    mtn_api_user = EncryptedCharField(blank=True)
    mtn_api_key = EncryptedCharField(blank=True)
    mtn_target_env = models.CharField(max_length=50, default='sandbox')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("branch", "provider")]

    def get_credentials(self):
        return {"provider": self.provider, "merchant_id": self.merchant_id,
                "api_key": self.api_key, "api_secret": self.api_secret, "extra": self.extra_config}

    @classmethod
    def resolve_for_branch(cls, branch):
        qs = cls.objects.filter(branch=branch, is_enabled=True)
        return qs.filter(is_default=True).first() or qs.first()


class PaymentTransaction(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    invoice = models.ForeignKey("sales.Invoice", on_delete=models.CASCADE, related_name="payments")
    payment_method = models.CharField(max_length=20)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20, default="PENDING")
    reference = models.CharField(max_length=100, unique=True)
    phone_number = models.CharField(max_length=20, blank=True)
    gateway_response = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)


class GatewayTransaction(models.Model):
    STATUS = [
        ("PENDING", "Pending USSD Approval"),
        ("SUCCESS", "Successful"),
        ("FAILED", "Failed"),
        ("CANCELLED", "Cancelled"),
    ]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    branch = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    provider = models.CharField(max_length=50) # MTN_DIRECT, STRIPE, etc.
    reference_id = models.CharField(max_length=100, unique=True)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    phone = models.CharField(max_length=20, blank=True)
    status = models.CharField(max_length=20, choices=STATUS, default="PENDING")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.provider} - {self.reference_id}"
