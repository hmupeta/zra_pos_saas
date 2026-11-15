"""Phase 2C v2: robust fix for subscriptions columns + sales ZRA fields."""
import os, sys, re

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()
from django.db import connection

# ======================================================================
# PART 1 — Fix subscriptions DB columns (raw SQL, bypasses stuck migrations)
# ======================================================================
print("=" * 62)
print("PART 1 — Subscription columns")
print("=" * 62)

SUB_FIELDS = ["has_pos", "has_inventory", "has_zra_smart_invoice",
              "has_full_accounting", "has_dedicated_manager", "has_custom_sla"]

from subscriptions.models import Plan
model_fields = {f.name for f in Plan._meta.fields}
with connection.cursor() as cur:
    cur.execute("SELECT column_name FROM information_schema.columns "
                "WHERE table_name='subscriptions_plan'")
    db_cols = {r[0] for r in cur.fetchall()}

missing_db = [f for f in SUB_FIELDS if f in model_fields and f not in db_cols]
if missing_db:
    print(f"🔧 DB missing {len(missing_db)} columns — ALTER TABLE")
    with connection.cursor() as cur:
        for f in missing_db:
            cur.execute(f'ALTER TABLE subscriptions_plan '
                        f'ADD COLUMN IF NOT EXISTS "{f}" boolean NOT NULL DEFAULT true')
            print(f"   ✅ {f}")
else:
    print("✅ Subscription DB columns already in sync")

# ======================================================================
# PART 2 — Show actual Invoice / Shift class content
# ======================================================================
print("\n" + "=" * 62)
print("PART 2 — Sales model diagnostic")
print("=" * 62)

SALES_PATH = "sales/models.py"
with open(SALES_PATH, encoding="utf-8") as f:
    src = f.read()
lines = src.splitlines()

def find_class(lines, name):
    for i, line in enumerate(lines):
        if re.match(rf"^class {name}\b", line):
            start = i
            break
    else:
        return None
    end = len(lines)
    for j in range(start + 1, len(lines)):
        if lines[j].strip() and not lines[j][0].isspace():
            end = j
            break
    return (start, end)

for cls in ("Invoice", "Shift"):
    r = find_class(lines, cls)
    if not r:
        print(f"\n❌ class {cls} NOT FOUND")
        continue
    s, e = r
    print(f"\n📦 class {cls}() — lines {s+1} to {e}")
    print("─" * 62)
    for line in lines[s:min(s + 20, e)]:
        print(f"  {line}")
    if e - s > 20:
        print(f"  ... ({e - s - 20} more lines)")

# ======================================================================
# PART 3 — Robust injection using indentation, not field names
# ======================================================================
print("\n" + "=" * 62)
print("PART 3 — Field injection")
print("=" * 62)

def inject_robust(class_name, fields, sentinel_field):
    """Insert fields at end of class body (before Meta/def/next class)."""
    with open(SALES_PATH, encoding="utf-8") as f:
        content = f.read()

    if sentinel_field in content:
        print(f"ℹ️  {class_name}: already has '{sentinel_field}' — skipping")
        return False

    inner = content.splitlines(keepends=True)
    r = find_class(inner, class_name)
    if not r:
        print(f"❌ {class_name}: class not found")
        return False
    s, e = r
    class_indent = len(inner[s]) - len(inner[s].lstrip())

    # Insertion point: before first nested "class " or "def " in the class,
    # otherwise just before the next top-level statement
    insert_at = e
    for i in range(s + 1, e):
        stripped = inner[i].strip()
        if not stripped:
            continue
        cur_indent = len(inner[i]) - len(inner[i].lstrip())
        if cur_indent > class_indent and (
            stripped.startswith("class ") or stripped.startswith("def ")
        ):
            insert_at = i
            break

    new_lines = ["\n"] + [f + "\n" for f in fields] + ["\n"]
    inner[insert_at:insert_at] = new_lines

    with open(SALES_PATH, "w", encoding="utf-8") as f:
        f.writelines(inner)
    print(f"✅ {class_name}: inserted {len(fields)} field(s) at line {insert_at + 1}")
    return True

invoice_fields = [
    '    zra_status = models.CharField(',
    '        max_length=20,',
    '        choices=[("PENDING","Pending"),("SUBMITTED","Submitted"),',
    '                 ("FAILED","Failed"),("OFFLINE_QUEUED","Offline queued")],',
    '        default="PENDING", db_index=True,',
    '    )',
    '    zra_submitted_at = models.DateTimeField(null=True, blank=True, db_index=True)',
    '    zra_qr_data = models.TextField(blank=True)',
]
shift_fields = [
    '    zreport_number = models.CharField(max_length=50, blank=True, db_index=True)',
    '    zreport_submitted_at = models.DateTimeField(null=True, blank=True)',
    '    zreport_qr_data = models.TextField(blank=True)',
]

ch1 = inject_robust("Invoice", invoice_fields, "zra_status")
ch2 = inject_robust("Shift",   shift_fields,   "zreport_number")

if not (ch1 or ch2):
    print("\nℹ️  No edits made — verify manually or paste the class dumps above")
    sys.exit(0)

# ======================================================================
# PART 4 — Migrate
# ======================================================================
print("\n" + "=" * 62)
print("PART 4 — Migrations")
print("=" * 62)
from django.core.management import call_command
call_command("makemigrations", "sales", verbosity=1)
call_command("migrate", verbosity=1)

# ======================================================================
# PART 5 — Verify via DB columns (source of truth)
# ======================================================================
print("\n" + "=" * 62)
print("PART 5 — Verify DB columns")
print("=" * 62)

with connection.cursor() as cur:
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='sales_invoice' AND column_name LIKE 'zra%'"
    )
    inv_db = sorted(r[0] for r in cur.fetchall())
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='sales_shift' AND column_name LIKE 'zreport%'"
    )
    shift_db = sorted(r[0] for r in cur.fetchall())
    cur.execute(
        "SELECT column_name FROM information_schema.columns "
        "WHERE table_name='subscriptions_plan'"
    )
    sub_db = sorted(r[0] for r in cur.fetchall())

print(f"Invoice DB zra_*:  {inv_db}")
print(f"Shift DB zreport_*: {shift_db}")
print(f"Plan  new flags:    {[f for f in SUB_FIELDS if f in sub_db]}")

expected_inv = {"zra_receipt_number", "zra_validation_code", "zra_status",
                "zra_submitted_at", "zra_qr_data"}
expected_shift = {"zreport_number", "zreport_submitted_at", "zreport_qr_data"}

ok = True
if not expected_inv.issubset(set(inv_db)):
    print(f"❌ Invoice missing: {expected_inv - set(inv_db)}"); ok = False
if not expected_shift.issubset(set(shift_db)):
    print(f"❌ Shift missing: {expected_shift - set(shift_db)}"); ok = False
if not all(f in sub_db for f in SUB_FIELDS):
    print(f"❌ Plan missing: {[f for f in SUB_FIELDS if f not in sub_db]}"); ok = False

print("\n" + ("🎉 Phase 2C v2 COMPLETE — all schema fixes applied"
              if ok else "❌ Some columns still missing — see above"))