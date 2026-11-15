"""Phase 2F v2: fix ALLOWED_HOSTS, then run the same 4 tests."""
import os, sys, json

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()

# ── FIX: allow the test client's default hostname ──────────────────────
from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver"]
    print("✅ Added 'testserver' to ALLOWED_HOSTS (in-memory only)")

from django.test import Client
from django.urls import reverse, NoReverseMatch

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} {name}" + (f"  ({detail})" if detail else ""))

# ── Locate URL ──────────────────────────────────────────────────────────
def find_url(*names):
    for n in names:
        try:
            return reverse(n)
        except NoReverseMatch:
            continue
    return "/api/accounting/reports/trial-balance/"  # fallback

URL = find_url(
    "trial_balance", "accounting:trial_balance",
    "accounting_trial_balance", "trial-balance",
)
print(f"🎯 Test URL: {URL}")

# ── Setup ──────────────────────────────────────────────────────────────
from tenants.models import Company
from subscriptions.models import Plan, Subscription, TenantUsage
try:
    from core.models import User
except ImportError:
    from django.contrib.auth import get_user_model
    User = get_user_model()

print("\n" + "=" * 62); print("SETUP"); print("=" * 62)

basic = Plan.objects.get(name="Basic")
pro   = Plan.objects.get(name="Professional")

# Enforce policy: Basic has no accounting
if basic.has_full_accounting:
    basic.has_full_accounting = False; basic.save()
    print("  ⚠️  Fixed Basic.has_full_accounting -> False")
else:
    print("  ✅ Basic.has_full_accounting = False")

TEST_TPIN = "E2ETEST002"
Company.objects.filter(tpin=TEST_TPIN).delete()
company = Company.objects.create(name="_E2E_TEST_V2", tpin=TEST_TPIN)
Subscription.objects.create(company=company, plan=basic, is_active=True)
TenantUsage.objects.get_or_create(company=company)
print(f"  ✅ Tenant: {company.name}  (Basic)")

User.objects.filter(username="_e2e_tester_v2").delete()
tester = User.objects.create_user(
    username="_e2e_tester_v2", password="x",
    company=company, is_superuser=False, is_staff=False,
)
print(f"  ✅ User: {tester.username}  ->  {company.name}")

# ── TEST 1 ─────────────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("TEST 1 — Basic user blocked (expect 402)")
print("=" * 62)
c = Client(); c.force_login(tester)
r = c.get(URL)
check(f"HTTP {r.status_code} == 402", r.status_code == 402, f"got {r.status_code}")
if r.status_code == 402:
    try:
        body = json.loads(r.content)
        check("error == 'feature_not_available'",
              body.get("error") == "feature_not_available", body.get("error", ""))
        check("feature == 'has_full_accounting'",
              body.get("feature") == "has_full_accounting", body.get("feature", ""))
    except Exception as e:
        check("Response is valid JSON", False, str(e))

# ── TEST 2 ─────────────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("TEST 2 — Upgrade to Professional (expect 200)")
print("=" * 62)
sub = company.subscription; sub.plan = pro; sub.save()
print(f"  ✅ {company.name} -> Professional")
c2 = Client(); c2.force_login(tester)
r = c2.get(URL)
check(f"HTTP {r.status_code} == 200", r.status_code == 200, f"got {r.status_code}")

# ── TEST 3 ─────────────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("TEST 3 — Superuser bypass (expect 200)")
print("=" * 62)
su = User.objects.filter(is_superuser=True).first()
if su:
    c3 = Client(); c3.force_login(su)
    r = c3.get(URL)
    check(f"Superuser '{su.username}' gets {r.status_code} == 200",
          r.status_code == 200, f"got {r.status_code}")
else:
    print("  ⚠️  No superuser — skipping")

# ── TEST 4 ─────────────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("TEST 4 — Authenticated orphan (no company) blocked (expect 402)")
print("=" * 62)
User.objects.filter(username="_e2e_orphan_v2").delete()
orphan = User.objects.create_user(
    username="_e2e_orphan_v2", password="x", company=None, is_superuser=False,
)
c4 = Client(); c4.force_login(orphan)
r = c4.get(URL)
check(f"Orphan gets {r.status_code} == 402", r.status_code == 402, f"got {r.status_code}")

# ── Cleanup ────────────────────────────────────────────────────────────
print("\n" + "=" * 62); print("CLEANUP"); print("=" * 62)
tester.delete(); orphan.delete(); company.delete()
print(f"  ✅ Deleted test data")
print(f"  ✅ Remaining companies: {Company.objects.count()}")

# ── Summary ────────────────────────────────────────────────────────────
print("\n" + "=" * 62); print("SUMMARY"); print("=" * 62)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
for name, ok, _ in results:
    print(f"{'✅' if ok else '❌'} {name}")
print(f"\n{passed}/{total} passed")

if passed == total:
    print("\n🎉 Phase 2F end-to-end test PASSED")
    print("   Plan gating works end-to-end.")
    sys.exit(0)
else:
    print(f"\n❌ {total - passed} test(s) failed")
    sys.exit(1)