"""Fix sales/signals.py — rewrite with UTF-8 encoding + ASCII-safe content."""
import os, sys, py_compile

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

SIGNALS_PATH = "sales/signals.py"

# ── 1. Show current content (so we can see the bug) ──────────────────────
if os.path.exists(SIGNALS_PATH):
    with open(SIGNALS_PATH, "rb") as f:
        raw = f.read()
    print("=" * 62)
    print("CURRENT FILE — bytes 0..400")
    print("=" * 62)
    print(raw[:400])
    print("...")
    non_ascii = [(i, b) for i, b in enumerate(raw) if b > 127]
    if non_ascii:
        print(f"\n⚠️  Found {len(non_ascii)} non-ASCII byte(s): {non_ascii[:5]}")
        print("    This is the cause of the SyntaxError.")
    else:
        print("\nℹ️  File is pure ASCII — encoding is not the issue")

# ── 2. Rewrite cleanly ──────────────────────────────────────────────────
CLEAN = '''"""Sales signals — ZRA invoice compliance guard."""
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from sales.models import Invoice


@receiver(pre_save, sender=Invoice)
def enforce_zra_compliance(sender, instance, **kwargs):
    """Block transition to PAID if fiscalization has not been attempted.

    Rules enforced:
      - status='PAID' requires zra_status in (SUBMITTED, OFFLINE_QUEUED)
      - zra_status='SUBMITTED' requires zra_receipt_number
    """
    # Determine if this save transitions TO PAID
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

with open(SIGNALS_PATH, "w", encoding="utf-8") as f:
    f.write(CLEAN)
print(f"\n✅ Rewrote {SIGNALS_PATH} with UTF-8 + ASCII-only content")

# ── 3. Verify it compiles ──────────────────────────────────────────────
try:
    py_compile.compile(SIGNALS_PATH, doraise=True)
    print(f"✅ Compiles cleanly — syntax OK")
except py_compile.PyCompileError as e:
    print(f"❌ Still has syntax error: {e}")
    sys.exit(1)

# ── 4. Show final content for verification ──────────────────────────────
print("\n" + "=" * 62)
print("FINAL FILE")
print("=" * 62)
with open(SIGNALS_PATH, encoding="utf-8") as f:
    for i, line in enumerate(f, 1):
        print(f"  {i:2d}: {line.rstrip()}")

# ── 5. Sanity import test ───────────────────────────────────────────────
print("\n" + "=" * 62)
print("IMPORT TEST")
print("=" * 62)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django
try:
    django.setup()
    import sales.signals
    print("✅ import sales.signals → OK")
except Exception as e:
    print(f"❌ Failed: {type(e).__name__}: {e}")
    sys.exit(1)

print("\n🎉 Done — restart your Django server")