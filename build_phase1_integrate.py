import os
import subprocess
import sys

def run_command(command_list):
    print(f"⚙️  Running: {' '.join(command_list)}")
    try:
        result = subprocess.run(command_list, text=True, capture_output=True, check=True)
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"❌ Error executing: {' '.join(command_list)}")
        print(e.stderr)
        sys.exit(1)

def write_file(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip() + "\n")
    print(f"📝 Updated: {path}")

def main():
    print("🚀 Starting Phase 1 Integration: Multi-Tenant ZRA POS Foundation\n")

    # 1. Verify we are in the right directory
    if not os.path.exists("manage.py") or not os.path.exists("pos_backend"):
        print("❌ Error: Please run this script from the root directory (C:\\Users\\Howardm\\Documents\\django\\zra_pos_saas)")
        sys.exit(1)

    # 2. Update pos_backend/settings.py
    settings_path = "pos_backend/settings.py"
    with open(settings_path, "r") as f:
        settings_content = f.read()

    # Ensure our apps and DRF are in INSTALLED_APPS (safely)
    apps_to_add = ["'rest_framework'", "'tenants'", "'accounts'", "'subscriptions'"]
    for app in apps_to_add:
        if app not in settings_content:
            # Add right after staticfiles
            settings_content = settings_content.replace(
                "'django.contrib.staticfiles',",
                f"'django.contrib.staticfiles',\n    {app},"
            )
    
    # Add Middleware (safely)
    middleware = "'subscriptions.middleware.TenantLimitMiddleware',"
    if "TenantLimitMiddleware" not in settings_content:
        settings_content = settings_content.replace(
            "'django.contrib.auth.middleware.AuthenticationMiddleware',",
            f"'django.contrib.auth.middleware.AuthenticationMiddleware',\n    {middleware}"
        )
    
    with open(settings_path, "w") as f:
        f.write(settings_content)
    print(f"📝 Updated {settings_path} with Apps and Middleware")

    # 3. Inject Models into existing apps
    # We use 'append' logic or overwrite if they are empty defaults
    write_file("tenants/models.py", """
import uuid
from django.db import models

class Company(models.Model):
    \"\"\"The Tenant. Represents a single business entity paying for a subscription.\"\"\"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    tpin = models.CharField(max_length=10, unique=True, help_text="ZRA Taxpayer Identification Number")
    parent_company = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subsidiaries')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Branch(models.Model):
    \"\"\"A physical location of the Company. Limited by the subscription plan.\"\"\"
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=10)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True) # Used for downgrades

    class Meta:
        unique_together = ('company', 'branch_code')

    def __str__(self):
        return f"{self.company.name} - {self.name}"
""")

    write_file("subscriptions/models.py", """
from django.db import models
from tenants.models import Company

class Plan(models.Model):
    name = models.CharField(max_length=50) # Basic, Professional, Enterprise
    price_zmw = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Limits: Use -1 to represent "Unlimited"
    max_branches = models.IntegerField(default=1) 
    max_users = models.IntegerField(default=5)
    
    # Feature Flags
    has_api_access = models.BooleanField(default=False)
    has_multi_branch_reports = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class Subscription(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.company.name} - {self.plan.name}"

class TenantUsage(models.Model):
    \"\"\"Tracks current usage to avoid expensive COUNT(*) queries on every API call.\"\"\"
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='usage')
    current_branches = models.IntegerField(default=0)
    current_users = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
""")

    # 4. Generate Enforcement Logic
    write_file("subscriptions/middleware.py", """
from subscriptions.models import Subscription, TenantUsage

class TenantLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We check if the user has a 'company' attribute (you will need to add this to your core.User model)
        if request.user.is_authenticated and hasattr(request.user, 'company') and request.user.company:
            try:
                subscription = Subscription.objects.select_related('plan').get(company=request.user.company)
                usage, _ = TenantUsage.objects.get_or_create(company=request.user.company)
                request.tenant_plan = subscription.plan
                request.tenant_usage = usage
            except Subscription.DoesNotExist:
                request.tenant_plan = None
                request.tenant_usage = None
        return self.get_response(request)
""")

    write_file("subscriptions/signals.py", """
from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F
from tenants.models import Branch
from subscriptions.models import TenantUsage, Subscription

@receiver(pre_save, sender=Branch)
def enforce_branch_limit(sender, instance, **kwargs):
    if not instance.pk:
        with transaction.atomic():
            usage, _ = TenantUsage.objects.select_for_update().get_or_create(company=instance.company)
            try:
                sub = Subscription.objects.get(company=instance.company)
                if sub.plan.max_branches != -1 and usage.current_branches >= sub.plan.max_branches:
                    raise ValidationError(f"Limit reached: Plan allows {sub.plan.max_branches} branches.")
            except Subscription.DoesNotExist:
                pass # Handle if no subscription exists yet

@receiver(post_save, sender=Branch)
def update_branch_usage(sender, instance, created, **kwargs):
    if created:
        TenantUsage.objects.filter(company=instance.company).update(current_branches=F('current_branches') + 1)
""")

    # Register signals in subscriptions/apps.py
    write_file("subscriptions/apps.py", """
from django.apps import AppConfig

class SubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'subscriptions'

    def ready(self):
        import subscriptions.signals
""")

    # 5. Create Seed Script for Plans
    write_file("seed_plans.py", """
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from subscriptions.models import Plan

plans = [
    {"name": "Basic", "price_zmw": 500, "max_branches": 1, "max_users": 5, "has_api_access": False},
    {"name": "Professional", "price_zmw": 1500, "max_branches": 5, "max_users": 25, "has_api_access": True},
    {"name": "Enterprise", "price_zmw": 0, "max_branches": -1, "max_users": -1, "has_api_access": True},
]

for p in plans:
    obj, created = Plan.objects.get_or_create(name=p["name"], defaults=p)
    if created:
        print(f"✅ Seeded Plan: {p['name']}")
    else:
        print(f"ℹ️  Plan already exists: {p['name']}")
""")

    # 6. Run Migrations and Seed Data
    print("\n🗄️  Running Migrations for tenants and subscriptions...")
    run_command([sys.executable, "manage.py", "makemigrations", "tenants", "subscriptions"])
    run_command([sys.executable, "manage.py", "migrate"])
    
    print("\n🌱 Seeding Initial Pricing Plans...")
    run_command([sys.executable, "seed_plans.py"])

    print("\n🎉 Phase 1 Integration Complete!")
    print("⚠️  IMPORTANT NEXT STEP: You must manually add a 'company' ForeignKey to your existing User model (likely in core/models.py) linking to tenants.Company.")

if __name__ == "__main__":
    main()