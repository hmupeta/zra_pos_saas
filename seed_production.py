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
    
    # 1. Create Plans
    basic_plan, _ = Plan.objects.get_or_create(
        name="Basic", defaults={"price_zmw": 500, "max_branches": 1, "max_users": 5}
    )
    pro_plan, _ = Plan.objects.get_or_create(
        name="Professional", defaults={"price_zmw": 1500, "max_branches": 5, "max_users": 25, "has_full_accounting": True}
    )

    # 2. Create Tenant Company (SaaS Level)
    tenant_company, _ = TenantCompany.objects.get_or_create(
        tpin="TEST000001", defaults={"name": "Demo Store Ltd"}
    )
    Subscription.objects.get_or_create(company=tenant_company, defaults={"plan": pro_plan})
    TenantUsage.objects.get_or_create(company=tenant_company)

    # 3. Create Core Company and Tenant (POS Level)
    # Using get_or_create for Tenant to ensure it exists
    pos_tenant, _ = Tenant.objects.get_or_create(name="Demo Store Ltd")
    pos_company, _ = CoreCompany.objects.get_or_create(
        name="Demo Store Ltd", 
        defaults={"tenant": pos_tenant, "tpin": "TEST000001"}
    )

    # 4. Create Branch
    branch, _ = Branch.objects.get_or_create(
        company=tenant_company, branch_code="HQ", defaults={"name": "Main Branch"}
    )

     # 5. Create Users
    if not User.objects.filter(username='admin').exists():
        # REMOVED branch=branch
        User.objects.create_superuser('admin', 'admin@example.com', 'Admin@123456', company=tenant_company, tenant=pos_tenant)
        print("Created admin")

    if not User.objects.filter(username='demo_owner').exists():
        # REMOVED branch=branch
        User.objects.create_user('demo_owner', 'demo@example.com', 'Demo@123456', company=tenant_company, tenant=pos_tenant, is_staff=True)
        print("Created demo_owner")

    # 6. Seed POS Data
    tax, _ = TaxRate.objects.get_or_create(name="VAT 16%", defaults={"rate": Decimal("16.00"), "company": pos_company, "tenant": pos_tenant})
    category, _ = Category.objects.get_or_create(name="Beverages", defaults={"company": pos_company, "tenant": pos_tenant})

    # Updated to match your actual Product fields (barcode, current_stock)
    products = [
        {"name": "Coca-Cola 500ml", "price": Decimal("10.00"), "barcode": "COKE500"},
        {"name": "Fanta Orange 500ml", "price": Decimal("10.00"), "barcode": "FANTA500"},
        {"name": "Bread Loaf", "price": Decimal("18.00"), "barcode": "BREAD01"},
    ]
    
    for p in products:
        Product.objects.get_or_create(
            company=pos_company,
            tenant=pos_tenant,
            barcode=p["barcode"], # <--- Changed from sku to barcode
            defaults={
                "name": p["name"],
                "selling_price": p["price"],
                "unit_cost": p["price"] * Decimal("0.8"), # <--- Changed cost_price to unit_cost
                "category": category,
                "tax_rate": tax,
                "current_stock": 100 # <--- Changed stock_quantity to current_stock
            }
        )
    
    print("Seed complete!")

if __name__ == "__main__":
    run()