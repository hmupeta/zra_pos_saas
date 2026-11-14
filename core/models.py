from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from .encryption import EncryptedCharField
from tenants.models import Company


class SubscriptionPlan(models.Model):
    """SaaS pricing tiers."""
    code = models.CharField(max_length=20, unique=True)  # TRIAL, BASIC, PRO, ENTERPRISE
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    monthly_price_zmw = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    yearly_price_zmw = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    trial_days = models.IntegerField(default=14)

    # Feature limits
    max_branches = models.IntegerField(default=1)
    max_users = models.IntegerField(default=3)
    max_devices = models.IntegerField(default=2)
    allow_multi_branch_reports = models.BooleanField(default=False)
    allow_api_access = models.BooleanField(default=False)
    allow_accounting = models.BooleanField(default=False)
    allow_returns = models.BooleanField(default=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["monthly_price_zmw"]

    def __str__(self):
        return f"{self.name} (K{self.monthly_price_zmw}/mo)"


class Tenant(models.Model):
    """Top-level SaaS customer (a business with one or more branches)."""
    STATUS = [
        ("TRIAL", "Trial"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("CANCELLED", "Cancelled"),
    ]

    code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=200)
    legal_name = models.CharField(max_length=200, blank=True)
    contact_email = models.EmailField()
    contact_phone = models.CharField(max_length=20)
    address = models.TextField(blank=True)
    country = models.CharField(max_length=50, default="Zambia")

    plan = models.ForeignKey(SubscriptionPlan, on_delete=models.PROTECT, null=True, blank=True)
    subscription_status = models.CharField(max_length=20, choices=STATUS, default="TRIAL")
    trial_ends_at = models.DateTimeField(null=True, blank=True)
    subscription_ends_at = models.DateTimeField(null=True, blank=True)

    billing_email = models.EmailField(blank=True)
    hq_tpin = models.CharField(max_length=20, blank=True)

    is_active = models.BooleanField(default=True)
    onboarded_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.code} - {self.name}"

    def is_operational(self):
        if not self.is_active:
            return False
        if self.subscription_status == "TRIAL":
            return self.trial_ends_at and self.trial_ends_at > timezone.now()
        return self.subscription_status == "ACTIVE"

    def branches_count(self):
        return self.branches.filter(is_active=True).count()

    def users_count(self):
        return self.users.filter(is_active=True).count()

    def within_plan_limits(self, resource, delta=1):
        if not self.plan:
            return True
        if resource == "branches":
            return self.branches_count() + delta <= self.plan.max_branches
        if resource == "users":
            return self.users_count() + delta <= self.plan.max_users
        return True


class User(AbstractUser):
    USER_TYPES = [
        ("PLATFORM_ADMIN", "Platform Admin"),
        ("TENANT_OWNER", "Tenant Admin (Owner)"),
        ("MANAGER", "Manager"),
        ("SALES_ADMIN", "Sales Admin"),
        ("SALES_AGENT", "Sales Agent"),
    ]
    EMPLOYMENT_STATUS = [
        ("PENDING", "Pending Approval"),
        ("ACTIVE", "Active"),
        ("SUSPENDED", "Suspended"),
        ("TERMINATED", "Terminated"),
    ]

    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, null=True, blank=True, related_name="users")
    user_type = models.CharField(max_length=20, choices=USER_TYPES, default="CASHIER")
    employment_status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS, default="ACTIVE")
    employee_id = models.CharField(max_length=30, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')


    # Security
    login_attempts = models.IntegerField(default=0)
    locked_until = models.DateTimeField(null=True, blank=True)
    two_factor_enabled = models.BooleanField(default=False)
    two_factor_secret = models.CharField(max_length=100, blank=True)
    password_expiry_date = models.DateTimeField(null=True, blank=True)

    # Onboarding
    invited_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="invited_users")
    invite_token = models.CharField(max_length=100, blank=True)
    approved_by = models.ForeignKey("self", on_delete=models.SET_NULL, null=True, blank=True, related_name="approved_users")
    approved_at = models.DateTimeField(null=True, blank=True)

    last_login_ip = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "core_user"

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

    def is_locked(self):
        return self.locked_until and timezone.now() < self.locked_until

    def is_platform_admin(self):
        return self.user_type == "PLATFORM_ADMIN"


class Company(models.Model):
    """A physical branch location. Belongs to exactly one Tenant."""
    name = models.CharField(max_length=200)
    tenant = models.ForeignKey(Tenant, on_delete=models.PROTECT, related_name="branches", null=True, blank=True)
    branch_code = models.CharField(max_length=20, default="001")
    tpin = models.CharField(max_length=20, help_text="ZRA Tax PIN for this branch")
    address = models.TextField()
    phone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    vat_registered = models.BooleanField(default=True)
    logo = models.ImageField(upload_to="branch_logos/", null=True, blank=True)

    # Per-branch ZRA configuration
    zra_vsdc_url = models.URLField(default="http://localhost:8080/vsdc-api/v1", blank=True)
    zra_device_serial = models.CharField(max_length=50, default="DVC00000001", blank=True)

    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]
        unique_together = [("tenant", "branch_code")]

    def __str__(self):
        return f"{self.tenant.code if self.tenant else '?'}/{self.name}"


class Device(models.Model):
    """A POS terminal."""
    device_id = models.CharField(max_length=50, unique=True)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="devices")
    serial_number = models.CharField(max_length=100)
    zra_device_code = models.CharField(max_length=100, blank=True)
    is_active = models.BooleanField(default=True)
    last_sync = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.device_id} @ {self.company.name}"


class BranchAccess(models.Model):
    """Many-to-many: user ↔ branches they can access."""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="branch_access")
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name="user_access")
    is_default = models.BooleanField(default=False)
    granted_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("user", "company")]

    def __str__(self):
        return f"{self.user.username} → {self.company.name}"


class AuditLog(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="audit_logs")
    tenant = models.ForeignKey(Tenant, on_delete=models.SET_NULL, null=True, blank=True)
    company = models.ForeignKey(Company, on_delete=models.SET_NULL, null=True, blank=True)
    action = models.CharField(max_length=100)
    details = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]

    def __str__(self):
        return f"{self.user} - {self.action}"


class LoginHistory(models.Model):
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name="login_history")
    username_attempted = models.CharField(max_length=150)
    success = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    failure_reason = models.CharField(max_length=255, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp"]


class SystemNotification(models.Model):
    TYPES = [
        ("INFO", "Information"),
        ("WARNING", "Warning"),
        ("ERROR", "Critical Error"),
        ("SUCCESS", "Success"),
    ]
    tenant = models.ForeignKey(Tenant, on_delete=models.CASCADE, related_name="notifications")
    title = models.CharField(max_length=200)
    message = models.TextField()
    notification_type = models.CharField(max_length=20, choices=TYPES, default="INFO")
    is_read = models.BooleanField(default=False)
    link = models.CharField(max_length=255, blank=True, help_text="Where to redirect when clicked")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.title} - {self.tenant.name}"
