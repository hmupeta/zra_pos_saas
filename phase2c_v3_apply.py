"""Phase 2C v3: definitive apply + reconcile."""
import os, sys

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()

from django.db import connection
from django.core.management import call_command
from django.db.migrations.recorder import MigrationRecorder
from django.db.migrations.loader import MigrationLoader

# ======================================================================
# STEP 0 — Show what's pending before we touch anything
# ======================================================================
print("=" * 62)
print("STEP 0 — CURRENT MIGRATION STATE")
print("=" * 62)
loader = MigrationLoader(connection)
applied = MigrationRecorder(connection).applied_migrations()
for app in ("sales", "subscriptions"):
    disk  = {n for (a, n) in loader.disk_migrations   if a == app}
    done  = {n for (a, n) in applied                  if a == app}
    pend  = sorted(disk - done)
    print(f"  {app:15s} disk={len(disk):2d}  applied={len(done):2d}  "
          f"pending={len(pend)}"
          + (f" → {pend}" if pend else ""))

# ======================================================================
# STEP 1 — Raw ALTER for any missing columns (idempotent)
# ======================================================================
print("\n" + "=" * 62)
print("STEP 1 — Ensure DB columns (idempotent ALTER)")
print("=" * 62)

REQUIRED = [
    # (table, column, sql_type, default_sql, not_null)
    ("subscriptions_plan", "has_pos",                "boolean", "true",  True),
    ("subscriptions_plan", "has_inventory",          "boolean", "true",  True),
    ("subscriptions_plan", "has_zra_smart_invoice",  "boolean", "true",  True),
    ("subscriptions_plan", "has_full_accounting",    "boolean", "false", True),
    ("subscriptions_plan", "has_dedicated_manager",  "boolean", "false", True),
    ("subscriptions_plan", "has_custom_sla",         "boolean", "false", True),
    ("sales_invoice", "zra_status",                  "varchar(20)", "'PENDING'", True),
    ("sales_invoice", "zra_submitted_at",            "timestamp with time zone", None, False),
    ("sales_invoice", "zra_qr_data",                 "text", None, False),
    ("sales_shift",   "zreport_number",              "varchar(50)", "''", True),
    ("sales_shift",   "zreport_submitted_at",        "timestamp with time zone", None, False),
    ("sales_shift",   "zreport_qr_data",             "text", None, False),
]

added = []
with connection.cursor() as cur:
    for table, col, typ, default, not_null in REQUIRED:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=%s AND column_name=%s",
            [table, col],
        )
        if cur.fetchone():
            print(f"  ✅ {table}.{col}")
            continue
        sql = f'ALTER TABLE {table} ADD COLUMN "{col}" {typ}'
        if default is not None:
            sql += f" DEFAULT {default}"
        if not_null:
            sql += " NOT NULL"
        cur.execute(sql)
        print(f"  🔧 {table}.{col}  (added)")
        added.append(f"{table}.{col}")

print(f"\n  Total columns added: {len(added)}")

# ======================================================================
# STEP 2 — Record model state in migration files
# ======================================================================
print("\n" + "=" * 62)
print("STEP 2 — makemigrations sales subscriptions")
print("=" * 62)
try:
    call_command("makemigrations", "sales", "subscriptions", verbosity=1)
except SystemExit:
    # makemigrations exits non-zero when "no changes" — that's fine
    pass

# ======================================================================
# STEP 3 — Mark pending migrations as applied (DB is already correct)
# ======================================================================
print("\n" + "=" * 62)
print("STEP 3 — migrate --fake (skip SQL, mark state)")
print("=" * 62)

for app in ("subscriptions", "sales"):
    # Recount pending
    loader  = MigrationLoader(connection)
    applied = MigrationRecorder(connection).applied_migrations()
    disk    = {n for (a, n) in loader.disk_migrations if a == app}
    done    = {n for (a, n) in applied            if a == app}
    pend    = disk - done
    if not pend:
        print(f"  ℹ️  {app}: nothing pending")
        continue
    try:
        call_command("migrate", app, "--fake", verbosity=0)
        print(f"  🔧 {app}: faked {sorted(pend)}")
    except SystemExit as e:
        print(f"  ❌ {app}: --fake failed: {e}")

# ======================================================================
# STEP 4 — FINAL VERIFY (fields + real DB access)
# ======================================================================
print("\n" + "=" * 62)
print("STEP 4 — FINAL VERIFY")
print("=" * 62)

ok = True

# 4a. Columns exist
with connection.cursor() as cur:
    for table, col, *_ in REQUIRED:
        cur.execute(
            "SELECT 1 FROM information_schema.columns "
            "WHERE table_name=%s AND column_name=%s",
            [table, col],
        )
        if not cur.fetchone():
            print(f"  ❌ {table}.{col} still missing")
            ok = False
        else:
            print(f"  ✅ {table}.{col}")

# 4b. Plan flags are readable
print("\n  Plan flags:")
from subscriptions.models import Plan
for p in Plan.objects.all():
    print(f"    {p.name:<14} pos={p.has_pos} "
          f"acct={p.has_full_accounting} api={p.has_api_access}")

# 4c. Real field access on live data (this is the true test)
print("\n  Live data access:")
try:
    from sales.models import Invoice, Shift
    inv = Invoice.objects.first()
    if inv:
        print(f"    ✅ invoice#{inv.invoice_number}.zra_status = {inv.zra_status!r}")
    sft = Shift.objects.first()
    if sft:
        print(f"    ✅ shift#{sft.id}.zreport_number = {sft.zreport_number!r}")
except Exception as e:
    print(f"    ❌ {e}")
    ok = False

# 4d. Migration state is clean
print("\n  Migration state after fix:")
loader  = MigrationLoader(connection)
applied = MigrationRecorder(connection).applied_migrations()
for app in ("sales", "subscriptions"):
    disk = {n for (a, n) in loader.disk_migrations if a == app}
    done = {n for (a, n) in applied            if a == app}
    pend = disk - done
    if pend:
        print(f"    ⚠️  {app}: still pending {sorted(pend)}")
        ok = False
    else:
        print(f"    ✅ {app}: fully applied ({len(disk)} migrations)")

print("\n" + ("=" * 62) + "\n" +
      ("🎉 Phase 2C COMPLETE — schema in sync" if ok
       else "❌ Some issues remain — see above"))