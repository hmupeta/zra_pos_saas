#!/usr/bin/env python
"""
test_phase1.py
==============
End-to-end verification of Phase 1 enforcement.

Creates a throwaway tenant, exercises the branch + user limits,
prints PASS/FAIL for each check, and cleans up afterward.
"""
import os, sys

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django
django.setup()

from django.core.exceptions import ValidationError
from tenants.models import Company, Branch
from subscriptions.models import Plan, Subscription, TenantUsage
from core.models import User  # adjust if your model lives elsewhere

PASS, FAIL, INFO = "✅ PASS", "❌ FAIL", "ℹ️  INFO"
results = []

def check(name, condition):
    tag = PASS if condition else FAIL
    results.append((tag, name))
    print(f"{tag}  {name}")

def show_current_state():
    print("=" * 62)
    print("📊 CURRENT DATABASE STATE")
    print("=" * 62)
    companies = Company.objects.all()
    print(f"Companies: {companies.count()}")
    for c in companies:
        sub = getattr(c, "subscription", None)
        plan_name = sub.plan.name if sub else "— none —"
        print(f"  • {c.name} (TPIN {c.tpin})  plan={plan_name}")
        print(f"      branches={c.branches.count()}  users={c.users.count()}")
    print()

def make_test_tenant():
    """Create a fresh tenant on the Basic plan for testing."""
    # Pick a unique TPIN (max 10 chars)
    base = "PH1TEST"
    suffix = 1
    while Company.objects.filter(tpin=f"{base}{suffix:03d}").exists():
        suffix += 1
        if suffix > 999:
            raise RuntimeError("Ran out of test TPINs")
    tpin = f"{base}{suffix:03d}"  # 10 chars: PH1TEST001

    company = Company.objects.create(name=f"_PHASE1_TEST_{suffix}", tpin=tpin)
    basic = Plan.objects.get(name="Basic")
    Subscription.objects.create(company=company, plan=basic, is_active=True)
    TenantUsage.objects.get_or_create(company=company)
    print(f"🧪 Created test tenant: {company.name} (TPIN {tpin})\n")
    return company

def test_branch_limit(company):
    print("─" * 62)
    print("🧪 TEST 1 — Branch limit (Basic = 1 branch)")
    print("─" * 62)

    # 1st branch should succeed
    try:
        Branch.objects.create(company=company, name="Main Branch", branch_code="MAIN")
        company.usage.refresh_from_db()
        check("1st branch created successfully", True)
        check("TenantUsage.current_branches == 1", company.usage.current_branches == 1)
    except Exception as e:
        check(f"1st branch created (got exception: {e})", False)
        return

    # 2nd branch should FAIL with ValidationError
    try:
        Branch.objects.create(company=company, name="Second Branch", branch_code="B2")
        check("2nd branch correctly BLOCKED", False)  # should not reach here
    except ValidationError as e:
        check("2nd branch correctly BLOCKED with ValidationError", True)
        print(f"     ↳ {str(e)[:70]}")
    except Exception as e:
        check(f"2nd branch blocked (unexpected exc: {type(e).__name__})", False)
    print()

def test_user_limit(company):
    print("─" * 62)
    print("🧪 TEST 2 — User limit (Basic = 5 users)")
    print("─" * 62)

    for i in range(1, 6):
        try:
            User.objects.create_user(
                username=f"ph1test_user_{i}_{company.id.hex[:6]}",
                email=f"ph1test{i}@example.invalid",
                password="x",
                company=company,
            )
        except Exception as e:
            check(f"User {i}/5 created (FAILED: {type(e).__name__}: {e})", False)
            return
    company.usage.refresh_from_db()
    check("5 users created", company.users.count() == 5)
    check("TenantUsage.current_users == 5", company.usage.current_users == 5)

    # 6th user should FAIL
    try:
        User.objects.create_user(
            username=f"ph1test_user_6_{company.id.hex[:6]}",
            email="ph1test6@example.invalid",
            password="x",
            company=company,
        )
        check("6th user correctly BLOCKED", False)
    except ValidationError as e:
        check("6th user correctly BLOCKED with ValidationError", True)
        print(f"     ↳ {str(e)[:70]}")
    except Exception as e:
        check(f"6th user blocked (unexpected exc: {type(e).__name__})", False)
    print()

def test_upgrade_unlocks(company):
    print("─" * 62)
    print("🧪 TEST 3 — Upgrade to Professional unlocks more branches")
    print("─" * 62)

    pro = Plan.objects.get(name="Professional")
    sub = company.subscription
    sub.plan = pro
    sub.save()
    company.refresh_from_db()

    try:
        Branch.objects.create(company=company, name="Branch #2 Pro", branch_code="B2PRO")
        Branch.objects.create(company=company, name="Branch #3 Pro", branch_code="B3PRO")
        check("Upgrade to Pro allowed 2nd + 3rd branch", True)
    except ValidationError as e:
        check(f"Upgrade to Pro still blocked: {e}", False)
    company.usage.refresh_from_db()
    check("TenantUsage.current_branches == 3", company.usage.current_branches == 3)
    print()

def cleanup(company):
    print("─" * 62)
    print("🧹 CLEANUP")
    print("─" * 62)
    # Detach users first (SET_NULL likely), then delete company
    User.objects.filter(company=company).delete()
    company.delete()
    check("Test tenant and its users removed", not Company.objects.filter(pk=company.pk).exists())
    print()

# ======================================================================
show_current_state()
test_co = make_test_tenant()
try:
    test_branch_limit(test_co)
    test_user_limit(test_co)
    test_upgrade_unlocks(test_co)
finally:
    cleanup(test_co)

print("=" * 62)
print("📋 SUMMARY")
print("=" * 62)
passed = sum(1 for tag, _ in results if tag == PASS)
failed = sum(1 for tag, _ in results if tag == FAIL)
print(f"   {passed} passed, {failed} failed, {len(results)} total")
print()
if failed:
    print("❌ Phase 1 enforcement has issues — see failures above.")
    sys.exit(1)
else:
    print("🎉 Phase 1 CONFIRMED — all tier enforcement works correctly.")