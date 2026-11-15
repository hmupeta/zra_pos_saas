"""Phase 2C: add missing ZRA compliance fields to Invoice + Shift."""
import os, sys

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()

# ── 1. Inspect existing zra_* fields on Invoice and Shift ───────────────
from sales.models import Invoice, Shift

print("=" * 62)
print("🔍 CURRENT ZRA FIELDS")
print("=" * 62)
inv_zra = sorted(f.name for f in Invoice._meta.fields if "zra" in f.name.lower())
shift_zra = sorted(f.name for f in Shift._meta.fields if "zra" in f.name.lower() or "zreport" in f.name.lower())
print(f"Invoice: {inv_zra or '(none)'}")
print(f"Shift:   {shift_zra or '(none)'}")

# ── 2. Report gaps ──────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("📋 GAP ANALYSIS")
print("=" * 62)

invoice_needs = []
if not any(f in inv_zra for f in ("zra_status", "fiscal_status")):
    invoice_needs.append("zra_status")
if not any(f in inv_zra for f in ("zra_submitted_at", "fiscalized_at")):
    invoice_needs.append("zra_submitted_at")
if not any(f in inv_zra for f in ("zra_qr_data", "zra_signature", "zra_internal_data")):
    invoice_needs.append("zra_qr_data")

shift_needs = []
if not any(f in shift_zra for f in ("zreport_number", "zreport_no")):
    shift_needs.append("zreport_number")
if not any(f in shift_zra for f in ("zreport_submitted_at",)):
    shift_needs.append("zreport_submitted_at")
if not any(f in shift_zra for f in ("zreport_qr_data", "zreport_qr")):
    shift_needs.append("zreport_qr_data")

print(f"Invoice needs: {invoice_needs or '✓ complete'}")
print(f"Shift needs:   {shift_needs or '✓ complete'}")

if not invoice_needs and not shift_needs:
    print("\n✅ All required ZRA fields already present")
    sys.exit(0)

# ── 3. Patch models.py files ────────────────────────────────────────────
def inject_fields(path, class_name, anchor_field, new_fields_src):
    """Inject new_fields_src after anchor_field line in class_name."""
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if new_fields_src.split("\n")[0].strip() in content:
        print(f"ℹ️  {class_name}: already patched")
        return
    # Find "class ClassName" then the first occurrence of anchor_field within
    idx = content.find(f"class {class_name}(")
    if idx < 0:
        print(f"❌ {class_name} not found in {path}")
        return
    # Find anchor_field after idx
    anchor_idx = content.find(f"{anchor_field} =", idx)
    if anchor_idx < 0:
        print(f"❌ anchor '{anchor_field} =' not found in {class_name}")
        return
    # Find end of that line
    eol = content.find("\n", anchor_idx)
    # Insert new fields after that line
    new_content = content[:eol+1] + "\n" + new_fields_src + "\n" + content[eol+1:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_content)
    print(f"✅ Patched {path} → {class_name}")

if invoice_needs:
    src = []
    if "zra_status" in invoice_needs:
        src.append(
            '    zra_status = models.CharField(\n'
            '        max_length=20,\n'
            '        choices=[("PENDING","Pending"),("SUBMITTED","Submitted"),\n'
            '                 ("FAILED","Failed"),("OFFLINE_QUEUED","Offline queued")],\n'
            '        default="PENDING", db_index=True,\n'
            '        help_text="Fiscalization lifecycle status",\n'
            '    )'
        )
    if "zra_submitted_at" in invoice_needs:
        src.append(
            '    zra_submitted_at = models.DateTimeField(null=True, blank=True, db_index=True)'
        )
    if "zra_qr_data" in invoice_needs:
        src.append(
            '    zra_qr_data = models.TextField(blank=True, help_text="Full QR / signed payload from VSDC")'
        )
    inject_fields("sales/models.py", "Invoice", "status", "\n".join(src))

if shift_needs:
    src = []
    if "zreport_number" in shift_needs:
        src.append('    zreport_number = models.CharField(max_length=50, blank=True, db_index=True)')
    if "zreport_submitted_at" in shift_needs:
        src.append('    zreport_submitted_at = models.DateTimeField(null=True, blank=True)')
    if "zreport_qr_data" in shift_needs:
        src.append('    zreport_qr_data = models.TextField(blank=True)')
    inject_fields("sales/models.py", "Shift", "is_closed", "\n".join(src))

# ── 4. Migrate ──────────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("⚙️  MIGRATIONS")
print("=" * 62)
from django.core.management import call_command
call_command("makemigrations", "sales", verbosity=1)
call_command("migrate", verbosity=1)

# ── 5. Verify ───────────────────────────────────────────────────────────
print("\n" + "=" * 62)
print("✔️  VERIFICATION")
print("=" * 62)
inv_now = sorted(f.name for f in Invoice._meta.fields if "zra" in f.name.lower())
shift_now = sorted(f.name for f in Shift._meta.fields if "zra" in f.name.lower() or "zreport" in f.name.lower())
print(f"Invoice zra_*: {inv_now}")
print(f"Shift zreport_*: {shift_now}")
print("\n🎉 Phase 2C complete")