"""
Seed data for POS SaaS backend. Safe to run multiple times (idempotent).
Run: python fix_seed.py
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
os.chdir(BACKEND_PATH)


SEED_SCRIPT = r'''
from decimal import Decimal
from datetime import timedelta
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import authenticate

print("=" * 60)
print("  SEEDING DATA")
print("=" * 60)
print(f"DB: {settings.DATABASES['default']['ENGINE']}")
print(f"Name: {settings.DATABASES['default']['NAME']}")
print()

from core.models import SubscriptionPlan, Tenant, Company, User, BranchAccess
from inventory.models import TaxRate, Category, Product
from accounting.models import Account
from payments.models import BranchPaymentConfig
from customers.models import Customer

# 1. Plans
print("--- Subscription plans ---")
plans = [
    {"code": "TRIAL", "name": "Free Trial", "monthly_price_zmw": 0, "trial_days": 14,
     "max_branches": 1, "max_users": 3, "max_devices": 2},
    {"code": "BASIC", "name": "Basic", "monthly_price_zmw": 500, "trial_days": 0,
     "max_branches": 1, "max_users": 5, "max_devices": 3},
    {"code": "PRO", "name": "Professional", "monthly_price_zmw": 1500, "trial_days": 0,
     "max_branches": 5, "max_users": 25, "max_devices": 10,
     "allow_multi_branch_reports": True, "allow_accounting": True, "allow_api_access": True},
    {"code": "ENTERPRISE", "name": "Enterprise", "monthly_price_zmw": 5000, "trial_days": 0,
     "max_branches": 999, "max_users": 999, "max_devices": 999,
     "allow_multi_branch_reports": True, "allow_accounting": True, "allow_api_access": True},
]
for p in plans:
    obj, c = SubscriptionPlan.objects.update_or_create(code=p["code"], defaults=p)
    print(f"  {'[+]' if c else '[=]'} {p['code']:11} {p['name']}")

# 2. Platform admin
print()
print("--- Platform admin ---")
admin, c = User.objects.get_or_create(
    username="admin",
    defaults={"email": "admin@yourstore.com", "user_type": "PLATFORM_ADMIN",
              "employment_status": "ACTIVE", "is_staff": True, "is_superuser": True},
)
admin.set_password("Admin@123456")
admin.user_type = "PLATFORM_ADMIN"
admin.employment_status = "ACTIVE"
admin.is_active = True
admin.is_staff = True
admin.is_superuser = True
admin.login_attempts = 0
admin.locked_until = None
admin.save()
print(f"  {'[+]' if c else '[reset]'} admin / Admin@123456")

# 3. Tenant
print()
print("--- Demo tenant ---")
pro = SubscriptionPlan.objects.get(code="PRO")
tenant, c = Tenant.objects.get_or_create(
    code="DEMO-001",
    defaults={
        "name": "Demo Store Zambia", "legal_name": "Demo Store Limited",
        "contact_email": "owner@demo.com", "contact_phone": "+260971234567",
        "address": "123 Cairo Road, Lusaka, Zambia", "country": "Zambia",
        "plan": pro, "subscription_status": "ACTIVE",
        "subscription_ends_at": timezone.now() + timedelta(days=365),
        "billing_email": "owner@demo.com", "hq_tpin": "1000000000",
        "onboarded_at": timezone.now(), "is_active": True,
    },
)
tenant.plan = pro
tenant.subscription_status = "ACTIVE"
tenant.subscription_ends_at = timezone.now() + timedelta(days=365)
tenant.is_active = True
tenant.save()
print(f"  {'[+]' if c else '[=]'} {tenant.name} ({tenant.code})")

# 4. Branch
print()
print("--- Branch ---")
branch, c = Company.objects.get_or_create(
    tenant=tenant, branch_code="001",
    defaults={
        "name": "Demo Main Branch", "tpin": "1000000000",
        "address": "123 Cairo Road, Lusaka", "phone": "+260211234567",
        "email": "main@demo.com", "vat_registered": True,
        "zra_vsdc_url": "http://localhost:8080/vsdc-api/v1",
        "zra_device_serial": "DEMO-POS-001", "is_active": True,
    },
)
branch.is_active = True
branch.save()
print(f"  {'[+]' if c else '[=]'} {branch.name}")

# 5. Owner (the critical login fix)
print()
print("--- Demo owner ---")
owner, c = User.objects.get_or_create(
    username="demo_owner",
    defaults={"email": "owner@demo.com", "first_name": "Demo", "last_name": "Owner",
              "tenant": tenant, "user_type": "TENANT_OWNER",
              "employment_status": "ACTIVE", "phone_number": "+260971234567",
              "is_active": True},
)
owner.email = "owner@demo.com"
owner.tenant = tenant
owner.user_type = "TENANT_OWNER"
owner.employment_status = "ACTIVE"
owner.is_active = True
owner.login_attempts = 0
owner.locked_until = None
owner.set_password("Demo@123456")
owner.save()
print(f"  {'[+]' if c else '[reset]'} demo_owner / Demo@123456")

# 6. Branch access
print()
print("--- Branch access ---")
ba, c = BranchAccess.objects.get_or_create(
    user=owner, company=branch, defaults={"is_default": True},
)
if not ba.is_default:
    ba.is_default = True
    ba.save()
print(f"  {'[+]' if c else '[=]'} demo_owner → {branch.name}")

# 7. Chart of accounts
print()
print("--- Chart of accounts ---")
accounts = [
    ("1000", "Cash on Hand", "ASSET", True),
    ("1010", "Bank Account", "ASSET", True),
    ("1100", "Accounts Receivable", "ASSET", True),
    ("1200", "Inventory", "ASSET", True),
    ("1400", "Input VAT", "ASSET", True),
    ("2000", "Accounts Payable", "LIABILITY", True),
    ("2100", "VAT Payable (ZRA)", "LIABILITY", True),
    ("3000", "Owner's Equity", "EQUITY", False),
    ("3100", "Retained Earnings", "EQUITY", True),
    ("4000", "Sales Revenue", "REVENUE", True),
    ("4010", "Sales Returns", "REVENUE", True),
    ("5000", "Cost of Goods Sold", "EXPENSE", True),
    ("5100", "Salaries & Wages", "EXPENSE", False),
    ("5200", "Rent", "EXPENSE", False),
    ("5300", "Utilities", "EXPENSE", False),
    ("5900", "Miscellaneous Expense", "EXPENSE", False),
]
count = 0
for code, name, t, ctrl in accounts:
    _, c = Account.objects.update_or_create(
        tenant=tenant, code=code,
        defaults={"name": name, "account_type": t, "is_control": ctrl},
    )
    if c: count += 1
print(f"  {len(accounts)} total ({count} new)")

# 8. Tax rates
print()
print("--- Tax rates ---")
tax16, _ = TaxRate.objects.get_or_create(
    tenant=tenant, name="VAT 16%",
    defaults={"tax_type": "STANDARD", "rate": Decimal("16"), "zra_tax_code": "A"},
)
TaxRate.objects.get_or_create(
    tenant=tenant, name="Zero Rated",
    defaults={"tax_type": "ZERO", "rate": Decimal("0"), "zra_tax_code": "C"},
)
print(f"  VAT 16% (A), Zero (C)")

# 9. Categories
print()
print("--- Categories ---")
cats = {}
for name, code in [("Beverages", "50202300"), ("Food & Groceries", "50190000"),
                   ("Household", "50131600")]:
    cat, _ = Category.objects.get_or_create(
        tenant=tenant, name=name,
        defaults={"zra_item_code": code, "is_active": True},
    )
    cats[name] = cat
print(f"  {len(cats)} categories")

# 10. Products
print()
print("--- Products ---")
products = [
    ("8901234567890", "Coca-Cola 500ml", "Beverages", 8.00, 5.60, 100),
    ("8901234567891", "Fanta Orange 500ml", "Beverages", 8.00, 5.60, 100),
    ("8901234567892", "Sprite 500ml", "Beverages", 8.00, 5.60, 100),
    ("8901234567893", "Water 1L", "Beverages", 5.00, 3.20, 200),
    ("8901234567894", "Bread Loaf", "Food & Groceries", 15.00, 11.00, 40),
    ("8901234567895", "Milk 1L", "Food & Groceries", 18.00, 14.00, 60),
    ("8901234567896", "Sugar 2kg", "Food & Groceries", 35.00, 28.00, 30),
    ("8901234567897", "Rice 5kg", "Food & Groceries", 95.00, 75.00, 25),
    ("8901234567898", "Cooking Oil 2L", "Food & Groceries", 55.00, 44.00, 35),
    ("8901234567899", "Soap Bar 250g", "Household", 12.00, 8.00, 50),
    ("8901234567800", "Detergent 1kg", "Household", 38.00, 28.00, 40),
    ("8901234567801", "Toothpaste 100ml", "Household", 22.00, 15.00, 45),
]
count = 0
for barcode, name, cat, price, cost, stock in products:
    _, c = Product.objects.update_or_create(
        tenant=tenant, barcode=barcode,
        defaults={"company": branch, "name": name, "category": cats[cat],
                  "tax_rate": tax16, "selling_price": Decimal(str(price)),
                  "unit_cost": Decimal(str(cost)), "current_stock": Decimal(str(stock)),
                  "reorder_level": Decimal("10"),
                  "zra_item_code": cats[cat].zra_item_code, "is_active": True},
    )
    if c: count += 1
print(f"  {len(products)} total ({count} new)")

# 11. Payment config
print()
print("--- Payment gateway ---")
pc, c = BranchPaymentConfig.objects.get_or_create(
    branch=branch, provider="MONEYUNIFY",
    defaults={"merchant_id": "demo-merchant-id", "api_key": "demo-api-key",
              "is_default": True, "is_enabled": True},
)
print(f"  {'[+]' if c else '[=]'} MoneyUnify")

# 12. Customers
print()
print("--- Customers ---")
customers = [
    ("CUST0001", "Mary", "Phiri", "+260971111111", "mary@example.com", 150),
    ("CUST0002", "John", "Banda", "+260972222222", "john@example.com", 320),
    ("CUST0003", "Grace", "Mulenga", "+260973333333", "grace@example.com", 85),
]
count = 0
for cid, fn, ln, phone, email, pts in customers:
    _, c = Customer.objects.update_or_create(
        tenant=tenant, customer_id=cid,
        defaults={"company": branch, "first_name": fn, "last_name": ln,
                  "phone_number": phone, "email": email,
                  "loyalty_points": Decimal(str(pts)), "kyc_status": "PENDING"},
    )
    if c: count += 1
print(f"  {len(customers)} total ({count} new)")

# SELF TEST
print()
print("=" * 60)
print("  SELF-TEST")
print("=" * 60)
print()

passed = 0
total = 4

u = authenticate(username="demo_owner", password="Demo@123456")
if u:
    print("  [PASS] demo_owner authenticate")
    passed += 1
else:
    print("  [FAIL] demo_owner authenticate")

u = authenticate(username="admin", password="Admin@123456")
if u:
    print("  [PASS] admin authenticate")
    passed += 1
else:
    print("  [FAIL] admin authenticate")

owner.refresh_from_db()
if owner.tenant_id == tenant.id:
    print(f"  [PASS] demo_owner has tenant ({tenant.code})")
    passed += 1
else:
    print("  [FAIL] demo_owner tenant mismatch")

if owner.branch_access.exists():
    print(f"  [PASS] demo_owner has {owner.branch_access.count()} branch access")
    passed += 1
else:
    print("  [FAIL] demo_owner has no branch access")

print()
if passed == total:
    print("=" * 60)
    print("  ✅ ALL TESTS PASSED")
    print("=" * 60)
else:
    print("=" * 60)
    print(f"  ⚠ {passed}/{total} passed")
    print("=" * 60)

print()
print("LOGIN:")
print("  Admin:      admin       / Admin@123456  →  /admin")
print("  Tenant:     demo_owner  / Demo@123456   →  /pos")
print()
print(f"  Tenant:     {tenant.name}")
print(f"  Branch:     {branch.name}")
print(f"  Products:   {Product.objects.filter(tenant=tenant).count()}")
print(f"  Customers:  {Customer.objects.filter(tenant=tenant).count()}")
print(f"  Accounts:   {Account.objects.filter(tenant=tenant).count()}")
print()
'''


def main():
    venv = BACKEND_PATH / "venv"
    python = (venv / "Scripts" / "python.exe") if platform.system() == "Windows" \
        else (venv / "bin" / "python")

    if not python.exists():
        print(f"[ERROR] venv not found: {python}")
        print("        Activate venv first: .\\venv\\Scripts\\Activate.ps1")
        sys.exit(1)

    seed_file = BACKEND_PATH / "_seed_runner.py"
    seed_file.write_text(SEED_SCRIPT, encoding="utf-8")
    try:
        subprocess.run(
            [str(python), "manage.py", "shell", "-c",
             f"exec(open('{seed_file.name}', encoding='utf-8').read())"],
            cwd=BACKEND_PATH, check=False,
        )
    finally:
        seed_file.unlink(missing_ok=True)


if __name__ == "__main__":
    main()