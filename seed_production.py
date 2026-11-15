import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from tenants.models import Company as TenantCompany, Branch
from subscriptions.models import Plan, Subscription, TenantUsage
from inventory.models import Product, Category, TaxRate
from core.models import Company as CoreCompany, Tenant
from decimal import Decimal

User = get_user_model()

def run():
    print("Starting production seed...")
    
    # 1. Create Plans (SaaS level)
    basic_plan, _ = Plan.objects.get_or_create(
        name="Basic", defaults={"price_zmw": 500, "max_branches": 1, "max_users": 5}
    )
    pro_plan, _ = Plan.objects.get_or_create(
        name="Professional", defaults={"price_zmw": 1500, "max_branches": 5, "max_users": 25, "has_full_accounting": True}
    )

    # 2. Create Tenant (Core Level)
    pos_tenant, _ = Tenant.objects.get_or_create(
        code="DEMO", defaults={"name": "Demo Store Ltd"}
    )

    # 3. Create Company (Core Level - Represents the physical branch)
    pos_company, _ = CoreCompany.objects.get_or_create(
        tenant=pos_tenant,
        branch_code="HQ",
        defaults={
            "name": "Demo Store HQ", 
            "tpin": "TEST000001"
        }
    )

    # 4. Create SaaS Company & Subscription (Tenant Level)
    tenant_company, _ = TenantCompany.objects.get_or_create(
        tpin="TEST000001", defaults={"name": "Demo Store Ltd"}
    )
    Subscription.objects.get_or_create(company=tenant_company, defaults={"plan": pro_plan})
    TenantUsage.objects.get_or_create(company=tenant_company)
    
    # Create SaaS Branch
    saas_branch, _ = Branch.objects.get_or_create(
        company=tenant_company, branch_code="HQ", defaults={"name": "Main Branch"}
    )

    # 5. Create Users (No 'branch' field, just 'company' and 'tenant')
    if not User.objects.filter(username='admin').exists():
        User.objects.create_superuser(
            'admin', 'admin@example.com', 'Admin@123456', 
            company=pos_company, tenant=pos_tenant, user_type='PLATFORM_ADMIN'
        )
        print("Created admin")

    if not User.objects.filter(username='demo_owner').exists():
        User.objects.create_user(
            'demo_owner', 'demo@example.com', 'Demo@123456', 
            company=pos_company, tenant=pos_tenant, user_type='OWNER', is_staff=True
        )
        print("Created demo_owner")

    # 6. Seed POS Data
    # TaxRate only requires tenant, name, rate, tax_type
    tax, _ = TaxRate.objects.get_or_create(
        tenant=pos_tenant, name="VAT 16%", 
        defaults={"rate": Decimal("16.00"), "tax_type": "VAT", "zra_tax_code": "A"}
    )
    
    # Category requires tenant, company, name
    category, _ = Category.objects.get_or_create(
        tenant=pos_tenant, company=pos_company, name="Beverages"
    )

    # Product fields verified
    products = [
        {"name": "Coca-Cola 500ml", "price": Decimal("10.00"), "barcode": "COKE500"},
        {"name": "Fanta Orange 500ml", "price": Decimal("10.00"), "barcode": "FANTA500"},
        {"name": "Bread Loaf", "price": Decimal("18.00"), "barcode": "BREAD01"},
    ]
    
    for p in products:
        Product.objects.get_or_create(
            tenant=pos_tenant,
            company=pos_company,
            barcode=p["barcode"],
            defaults={
                "name": p["name"],
                "selling_price": p["price"],
                "unit_cost": p["price"] * Decimal("0.8"),
                "category": category,
                "tax_rate": tax,
                "current_stock": 100
            }
        )
    
    print("Seed complete!")

if __name__ == "__main__":
    run()