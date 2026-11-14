import os
import subprocess
import sys

# --- Helper Functions ---

def run_command(command):
    """Runs a terminal command and exits if it fails."""
    print(f"⚙️  Running: {command}")
    result = subprocess.run(command, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Error executing: {command}")
        print(result.stderr)
        sys.exit(1)

def write_file(path, content):
    """Writes content to a file, creating directories if needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        f.write(content.strip() + "\n")
    print(f"📝 Created: {path}")

def append_to_file(path, content):
    """Appends content to a file."""
    with open(path, "a") as f:
        f.write(content.strip() + "\n")
    print(f"➕ Updated: {path}")

# --- Main Build Script ---

def main():
    print("🚀 Starting Phase 1 Build: Multi-Tenant ZRA POS Foundation\n")

    # 1. Initialize Environment & Project
    # Assumes you are in a directory with a virtual environment activated
    run_command("pip install django djangorestframework psycopg2-binary")
    run_command("django-admin startproject config .")
    
    # 2. Create Apps
    apps = ["tenants", "accounts", "subscriptions"]
    for app in apps:
        run_command(f"python manage.py startapp {app}")

    # 3. Update settings.py
    settings_path = "config/settings.py"
    with open(settings_path, "r") as f:
        settings_content = f.read()

    # Add to INSTALLED_APPS
    settings_content = settings_content.replace(
        "'django.contrib.staticfiles',",
        "'django.contrib.staticfiles',\n    'rest_framework',\n    'tenants',\n    'accounts',\n    'subscriptions',"
    )
    
    # Add Middleware
    settings_content = settings_content.replace(
        "'django.contrib.auth.middleware.AuthenticationMiddleware',",
        "'django.contrib.auth.middleware.AuthenticationMiddleware',\n    'subscriptions.middleware.TenantLimitMiddleware',"
    )
    
    # Add Custom User Model
    settings_content += "\nAUTH_USER_MODEL = 'accounts.User'\n"
    
    with open(settings_path, "w") as f:
        f.write(settings_content)
    print("📝 Updated settings.py with Apps, Middleware, and Custom User Model")

    # 4. Generate Models
    # --- Tenants App ---
    write_file("tenants/models.py", """
import uuid
from django.db import models

class Company(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    tpin = models.CharField(max_length=10, unique=True)
    parent_company = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subsidiaries')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Branch(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=10)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('company', 'branch_code')

    def __str__(self):
        return f"{self.company.name} - {self.name}"
""")

    # --- Accounts App ---
    write_file("accounts/models.py", """
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import gettext_lazy as _
from tenants.models import Company, Branch

class User(AbstractUser):
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='users', null=True, blank=True)
    branch = models.ForeignKey(Branch, on_delete=models.SET_NULL, null=True, blank=True, related_name='users')
    
    class Role(models.TextChoices):
        ADMIN = 'ADMIN', _('Admin')
        MANAGER = 'MANAGER', _('Manager')
        CASHIER = 'CASHIER', _('Cashier')
    
    role = models.CharField(max_length=50, choices=Role.choices, default=Role.CASHIER)

    def __str__(self):
        return f"{self.username} ({self.company.name if self.company else 'No Company'})"
""")

    # --- Subscriptions App ---
    write_file("subscriptions/models.py", """
from django.db import models
from tenants.models import Company

class Plan(models.Model):
    name = models.CharField(max_length=50)
    price_zmw = models.DecimalField(max_digits=10, decimal_places=2)
    max_branches = models.IntegerField(default=1) # -1 for unlimited
    max_users = models.IntegerField(default=5)    # -1 for unlimited
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
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='usage')
    current_branches = models.IntegerField(default=0)
    current_users = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
""")

    # 5. Generate Enforcement Logic
    # --- Middleware ---
    write_file("subscriptions/middleware.py", """
from subscriptions.models import Subscription, TenantUsage

class TenantLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
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

    # --- Signals (Enforcement) ---
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
            usage = TenantUsage.objects.select_for_update().get(company=instance.company)
            sub = Subscription.objects.get(company=instance.company)
            if sub.plan.max_branches != -1 and usage.current_branches >= sub.plan.max_branches:
                raise ValidationError(f"Limit reached: Plan allows {sub.plan.max_branches} branches.")

@receiver(post_save, sender=Branch)
def update_branch_usage(sender, instance, created, **kwargs):
    if created:
        TenantUsage.objects.filter(company=instance.company).update(current_branches=F('current_branches') + 1)
""")

    # Register signals in apps.py
    write_file("subscriptions/apps.py", """
from django.apps import AppConfig

class SubscriptionsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'subscriptions'

    def ready(self):
        import subscriptions.signals
""")

    # 6. Create Seed Script for Plans
    write_file("seed_plans.py", """
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from subscriptions.models import Plan

plans = [
    {"name": "Basic", "price_zmw": 500, "max_branches": 1, "max_users": 5, "has_api_access": False},
    {"name": "Professional", "price_zmw": 1500, "max_branches": 5, "max_users": 25, "has_api_access": True},
    {"name": "Enterprise", "price_zmw": 0, "max_branches": -1, "max_users": -1, "has_api_access": True},
]

for p in plans:
    Plan.objects.get_or_create(name=p["name"], defaults=p)
    print(f"✅ Seeded Plan: {p['name']}")
""")

    # 7. Run Migrations and Seed Data
    print("\n🗄️  Running Migrations...")
    run_command("python manage.py makemigrations tenants accounts subscriptions")
    run_command("python manage.py migrate")
    
    print("\n🌱 Seeding Initial Pricing Plans...")
    run_command("python seed_plans.py")

    print("\n🎉 Phase 1 Orchestration Complete!")
    print("Your multi-tenant foundation is ready. You can now start the server with: python manage.py runserver")

if __name__ == "__main__":
    main()