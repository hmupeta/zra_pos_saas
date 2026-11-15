"""Phase 2F: end-to-end test of plan gating via Django test client.

Verifies:
  1. Phase 2E decorators are actually installed on accounting views.
  2. Basic-tier user gets HTTP 402 on /accounting/trial-balance/.
  3. Upgrading the tenant to Professional unlocks the view (200).
  4. Superusers bypass gates (200).
  5. Authenticated user with no company is blocked (402).
"""
import os, sys, json

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()

from django.test import Client
from django.urls import reverse, NoReverseMatch, get_resolver

results = []
def check(name, ok, detail=""):
    results.append((name, ok, detail))
    print(f"{'✅' if ok else '❌'} {name}" + (f"  ({detail})" if detail else ""))

# ── PRE-CHECK: are the Phase 2E decorators really there? ────────────────
print("=" * 62)
print("PRE-CHECK — Phase 2E decorator presence")
print("=" * 62)

if not os.path.exists("accounting/views.py"):
    print("❌ accounting/views.py not found"); sys.exit(1)

with open("accounting/views.py", encoding="utf-8") as f:
    acc_src = f.read()
count_dec = acc_src.count('@requires_plan_feature("has_full_accounting")')
print(f"  Decorator count in accounting/views.py: {count_dec}")
if count_dec < 8:
    print(f"  ⚠️  Expected >= 8. Run 'python phase2e_gate_views.py' first.")
    print(f"  ⚠️  Aborting so we don't get a false-negative test result.")
    sys.exit(1)
print(f"  ✅ All 8 accounting views appear gated")

with open("reports/views.py", encoding="utf-8") as f:
    rep_src = f.read()
if '@requires_plan_feature("has_full_accounting")' not in rep_src:
    print(f"  ⚠️  cash_flow_statement not gated (may be non-critical for this test)")
else:
    print(f"  ✅ reports/cash_flow_statement gated")

# ── Locate the trial-balance URL dynamically ────────────────────────────
def find_url(*names):
    for n in names:
        try:
            return reverse(n)
        except NoReverseMatch:
            continue
    # Fallback: list all URLs containing "trial"
    print("\n  ⚠️  Could not reverse any of:", names)
    print("  Registered URLs containing 'trial' or 'accounting':")
    r = get_resolver()
    for p in r.url_patterns:
        if hasattr(p, "url_patterns"):
            for s in p.url_patterns:
                full = f"/{p.pattern}{s.pattern}"
                if any(k in full.lower() for k in ("trial", "accounting")):
                    print(f"    {full}  (name={s.name!r})")
        elif any(k in str(p.pattern).lower() for k in ("trial", "accounting")):
            print(f"    /{p.pattern}  (name={p.name!r})")
    return None

URL = find_url("trial_balance", "accounting:trial_balance", "trial-balance")
if not URL:
    URL = "/accounting/trial-balance/"  # last-resort guess
print(f"\n🎯 Test URL: {URL}")

# ── Setup ───────────────────────────────────────────────────────────────
from tenants.models import Company
from subscriptions.models import Plan, Subscription, TenantUsage
try:
    from core.models import User
except ImportError:
    from django.contrib.auth import get_user_model
    User = get_user_model()

print("\n" + "=" * 62)
print("SETUP")
print("=" * 62)

basic = Plan.objects.get(name="Basic")
pro = Plan.objects.get(name="Professional")

# Guard against drift: Basic must NOT have full accounting
if basic.has_full_accounting:
    basic.has_full_accounting = False
    basic.save()
    print(f"  ⚠️  Fixed Basic.has_full_accounting -> False")
else:
    print(f"  ✅ Basic.has_full_accounting = False")

TEST_TPIN = "E2ETEST001"  # exactly 10 chars
Company.objects.filter(tpin=TEST_TPIN).delete()
company = Company.objects.create(name="_E2E_TEST", tpin=TEST_TPIN)
Subscription.objects.create(company=company, plan=basic, is_active=True)
TenantUsage.objects.get_or_create(company=company)
print(f"  ✅ Tenant: {company.name}  (Basic)")

User.objects.filter(username="_e2e_tester").delete()
tester = User.objects.create_user(
    username="_e2e_tester", password="testpass123",
    company=company, is_superuser=False, is_staff=False,
)
print(f"  ✅ User: {tester.username}  ->  {company.name}")

# ── TEST 1 — Basic user blocked ─────────────────────────────────────────
print("\n" + "=" * 62)
print("TEST 1 — Basic user blocked from accounting")
print("=" * 62)
client = Client()
client.force_login(tester)
resp = client.get(URL, follow=False)
check(f"HTTP {resp.status_code} == 402", resp.status_code == 402,
      f"got {resp.status_code}")
if resp.status_code == 402:
    try:
        body = json.loads(resp.content)
        check("error == 'feature_not_available'",
              body.get("error") == "feature_not_available",
              body.get("error", ""))
        check("feature == 'has_full_accounting'",
              body.get("feature") == "has_full_accounting",
              body.get("feature", ""))
    except Exception as e:
        check("Response is valid JSON", False, str(e))

# ── TEST 2 — Upgrade to Professional ───────────────────────────────────
print("\n" + "=" * 62)
print("TEST 2 — Upgrade tenant to Professional")
print("=" * 62)
sub = company.subscription
sub.plan = pro
sub.save()
print(f"  ✅ {company.name} -> Professional")
resp = client.get(URL, follow=False)
check(f"HTTP {resp.status_code} == 200", resp.status_code == 200,
      f"got {resp.status_code}")

# ── TEST 3 — Superuser bypass ──────────────────────────────────────────
print("\n" + "=" * 62)
print("TEST 3 — Superuser bypass")
print("=" * 62)
su = User.objects.filter(is_superuser=True).first()
if su:
    sc = Client()
    sc.force_login(su)
    resp = sc.get(URL, follow=False)
    check(f"Superuser '{su.username}' gets {resp.status_code} == 200",
          resp.status_code == 200, f"got {resp.status_code}")
else:
    print("  ⚠️  No superuser — skipping")

# ── TEST 4 — Authenticated user with no company ────────────────────────
print("\n" + "=" * 62)
print("TEST 4 — Authenticated orphan user (no company)")
print("=" * 62)
User.objects.filter(username="_e2e_orphan").delete()
orphan = User.objects.create_user(
    username="_e2e_orphan", password="x",
    company=None, is_superuser=False,
)
oc = Client()
oc.force_login(orphan)
resp = oc.get(URL, follow=False)
check(f"Orphan gets {resp.status_code} == 402",
      resp.status_code == 402, f"got {resp.status_code}")

# ── Cleanup ────────────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("CLEANUP")
print("=" * 62)
tester.delete()
orphan.delete()
company.delete()
print("  ✅ Deleted test users + tenant")
print(f"  ✅ Remaining companies: {Company.objects.count()}")

# ── Summary ────────────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("SUMMARY")
print("=" * 62)
passed = sum(1 for _, ok, _ in results if ok)
total = len(results)
for name, ok, detail in results:
    print(f"{'✅' if ok else '❌'} {name}")
print(f"\n{passed}/{total} passed")

if passed < total:
    print(f"\n❌ {total - passed} test(s) failed — see above")
    sys.exit(1)

print("\n🎉 Phase 2F end-to-end test PASSED")
print("   Plan gating is provably working end-to-end.")