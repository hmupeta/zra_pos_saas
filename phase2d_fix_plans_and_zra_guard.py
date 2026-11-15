"""Phase 2D: fix plan flags + add ZRA invoice guard + audit gated views."""
import os, sys, re

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()

# ======================================================================
# PART 1 — Fix plan flags
# ======================================================================
print("=" * 62)
print("PART 1 — Fix plan flags to match pricing page")
print("=" * 62)

from subscriptions.models import Plan

CORRECT = {
    "Basic": {
        "has_pos": True, "has_inventory": True, "has_zra_smart_invoice": True,
        "has_full_accounting": False, "has_multi_branch_reports": False,
        "has_api_access": False, "has_dedicated_manager": False,
        "has_custom_sla": False,
    },
    "Professional": {
        "has_pos": True, "has_inventory": True, "has_zra_smart_invoice": True,
        "has_full_accounting": True, "has_multi_branch_reports": True,
        "has_api_access": True, "has_dedicated_manager": False,
        "has_custom_sla": False,
    },
    "Enterprise": {
        "has_pos": True, "has_inventory": True, "has_zra_smart_invoice": True,
        "has_full_accounting": True, "has_multi_branch_reports": True,
        "has_api_access": True, "has_dedicated_manager": True,
        "has_custom_sla": True,
    },
}

for name, flags in CORRECT.items():
    try:
        p = Plan.objects.get(name=name)
    except Plan.DoesNotExist:
        print(f"  ⚠️  {name} not found"); continue
    changed = [f"{k}={v}" for k, v in flags.items() if hasattr(p, k) and getattr(p, k) != v]
    if changed:
        for k, v in flags.items():
            if hasattr(p, k):
                setattr(p, k, v)
        p.save()
        print(f"  🔧 {name}: {', '.join(changed)}")
    else:
        print(f"  ✅ {name}: already correct")

# ======================================================================
# PART 2 — Add ZRA invoice guard
# ======================================================================
print("\n" + "=" * 62)
print("PART 2 — Add ZRA invoice guard")
print("=" * 62)

SIGNALS_PATH = "sales/signals.py"
MARKER = "# --- ZRA invoice compliance guard ---"

# Bootstrap the signals file if missing
if not os.path.exists(SIGNALS_PATH):
    with open(SIGNALS_PATH, "w") as f:
        f.write("from django.db.models.signals import pre_save\n")
        f.write("from django.dispatch import receiver\n")
        f.write("from django.core.exceptions import ValidationError\n")
        f.write("from sales.models import Invoice\n")
    print(f"  ℹ️  Created {SIGNALS_PATH}")

with open(SIGNALS_PATH) as f:
    content = f.read()

if MARKER in content:
    print("  ℹ️  ZRA guard already present — skipping")
else:
    guard = '''

# --- ZRA invoice compliance guard ---
@receiver(pre_save, sender=Invoice)
def enforce_zra_compliance(sender, instance, **kwargs):
    """Block transition to PAID if fiscalization hasn't been attempted.

    ZRA rules we enforce:
      • status='PAID' requires zra_status in (SUBMITTED, OFFLINE_QUEUED)
      • zra_status='SUBMITTED' requires zra_receipt_number
    """
    # Only fire when transitioning TO PAID (not on every save of an already-paid invoice)
    if instance.pk:
        try:
            old_status = Invoice.objects.only("status").get(pk=instance.pk).status
        except Invoice.DoesNotExist:
            old_status = None
    else:
        old_status = None

    if instance.status == "PAID" and old_status != "PAID":
        if instance.zra_status not in ("SUBMITTED", "OFFLINE_QUEUED"):
            raise ValidationError(
                f"Invoice cannot be marked PAID: ZRA status is "
                f"'{instance.zra_status}'. Submit to VSDC first, or queue "
                f"offline (zra_status='OFFLINE_QUEUED')."
            )

    if instance.zra_status == "SUBMITTED" and not instance.zra_receipt_number:
        raise ValidationError(
            "zra_status='SUBMITTED' requires zra_receipt_number to be set."
        )
'''
    with open(SIGNALS_PATH, "w") as f:
        f.write(content.rstrip() + guard)
    print(f"  ✅ Added ZRA guard to {SIGNALS_PATH}")

# Ensure sales.apps.ready() imports signals
APPS_PATH = "sales/apps.py"
if os.path.exists(APPS_PATH):
    with open(APPS_PATH) as f:
        apps_src = f.read()
    if "import sales.signals" not in apps_src:
        if "def ready(self):" in apps_src:
            apps_src = apps_src.replace(
                "def ready(self):",
                "def ready(self):\n        import sales.signals",
                1,
            )
        else:
            apps_src = apps_src.rstrip() + "\n\n    def ready(self):\n        import sales.signals\n"
        with open(APPS_PATH, "w") as f:
            f.write(apps_src)
        print(f"  ✅ Wired sales.signals in {APPS_PATH}")
    else:
        print(f"  ℹ️  {APPS_PATH} already imports signals")

# ======================================================================
# PART 3 — Smoke test the guard
# ======================================================================
print("\n" + "=" * 62)
print("PART 3 — Smoke test ZRA guard")
print("=" * 62)

from sales.models import Invoice
from django.core.exceptions import ValidationError

test_inv = Invoice.objects.filter(status="PENDING").first()
if not test_inv:
    print("  ℹ️  No PENDING invoices to test with")
else:
    print(f"  Testing with invoice #{test_inv.invoice_number}")
    orig = dict(status=test_inv.status, zra_status=test_inv.zra_status,
                zra_receipt_number=test_inv.zra_receipt_number or "")

    # Test A: PAID without fiscalization → should be BLOCKED
    try:
        test_inv.status = "PAID"
        test_inv.zra_status = "PENDING"
        test_inv.save()
        print("  ❌ Test A failed: PAID without fiscalization was allowed")
        test_inv.status = orig["status"]; test_inv.zra_status = orig["zra_status"]; test_inv.save()
    except ValidationError as e:
        print(f"  ✅ Test A: blocked ({str(e)[:55]}…)")
        test_inv.refresh_from_db()

    # Test B: PAID + OFFLINE_QUEUED → should be ALLOWED
    try:
        test_inv.status = "PAID"
        test_inv.zra_status = "OFFLINE_QUEUED"
        test_inv.save()
        print("  ✅ Test B: PAID + OFFLINE_QUEUED allowed (offline mode)")
        test_inv.refresh_from_db()
    except ValidationError as e:
        print(f"  ❌ Test B: offline mode blocked: {e}")

    # Test C: SUBMITTED without receipt → should be BLOCKED
    try:
        test_inv.status = "PAID"
        test_inv.zra_status = "SUBMITTED"
        test_inv.zra_receipt_number = ""
        test_inv.save()
        print("  ❌ Test C failed: SUBMITTED without receipt was allowed")
    except ValidationError as e:
        print(f"  ✅ Test C: blocked ({str(e)[:55]}…)")
        test_inv.refresh_from_db()

    # Test D: PAID + SUBMITTED + receipt → should be ALLOWED
    try:
        test_inv.status = "PAID"
        test_inv.zra_status = "SUBMITTED"
        test_inv.zra_receipt_number = "TEST-RCPT-001"
        test_inv.save()
        print("  ✅ Test D: PAID + SUBMITTED + receipt allowed (legit)")
    except ValidationError as e:
        print(f"  ❌ Test D: legitimate case blocked: {e}")

    # Restore original state
    test_inv.refresh_from_db()
    test_inv.status = orig["status"]
    test_inv.zra_status = orig["zra_status"]
    test_inv.zra_receipt_number = orig["zra_receipt_number"]
    test_inv.save()
    print(f"  ↩️  Restored invoice to original state")

# ======================================================================
# PART 4 — Audit gated views (report only, no changes)
# ======================================================================
print("\n" + "=" * 62)
print("PART 4 — Audit accounting / reports views (report only)")
print("=" * 62)

for path in ("accounting/views.py", "accounting/urls.py",
             "reports/views.py", "reports/urls.py"):
    if not os.path.exists(path):
        print(f"\n  ⚠️  {path} not found")
        continue
    with open(path) as f:
        src = f.read()
    funcs   = re.findall(r"^def (\w+)\s*\(", src, re.MULTILINE)
    classes = re.findall(r"^class (\w+)\s*\(", src, re.MULTILINE)
    print(f"\n  {path}")
    print(f"    functions ({len(funcs)}): {funcs or '(none)'}")
    print(f"    classes   ({len(classes)}): {classes or '(none)'}")

print("\n" + "=" * 62)
print("🎉 Phase 2D complete")
print("=" * 62)
print("""
⚠️  RESTART your Django server so the ZRA guard signal loads.
   Then verify:   python manage.py shell -c "import sales.signals; print('OK')"
""")