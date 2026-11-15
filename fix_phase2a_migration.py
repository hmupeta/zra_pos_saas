"""Diagnose + fix the Phase 2A migration mismatch."""
import os, sys

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()

from django.db import connection
from subscriptions.models import Plan

NEW_FIELDS = [
    "has_pos", "has_inventory", "has_zra_smart_invoice",
    "has_full_accounting", "has_dedicated_manager", "has_custom_sla",
]

print("=" * 62)
print("🔍 DIAGNOSIS")
print("=" * 62)

# 1. What does the Python model have?
model_fields = {f.name for f in Plan._meta.fields}
print(f"Model fields present: {', '.join(f for f in NEW_FIELDS if f in model_fields) or 'NONE'}")

# 2. What does the DB actually have?
with connection.cursor() as cur:
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'subscriptions_plan'
    """)
    db_cols = {row[0] for row in cur.fetchall()}
print(f"DB columns present:   {', '.join(f for f in NEW_FIELDS if f in db_cols) or 'NONE'}")

missing_in_model = [f for f in NEW_FIELDS if f not in model_fields]
missing_in_db    = [f for f in NEW_FIELDS if f not in db_cols]

if not missing_in_model and not missing_in_db:
    print("\n✅ Model and DB are in sync — nothing to fix")
    sys.exit(0)

# 3. Repair
print("\n" + "=" * 62)
print("🔧 REPAIR")
print("=" * 62)

if missing_in_model:
    print(f"⚠️  Model is missing {len(missing_in_model)} field(s).")
    print("   → Manually re-add them to subscriptions/models.py (the phase2a script edit didn't take).")
    print("   → Then run: python manage.py makemigrations subscriptions && python manage.py migrate")
    sys.exit(1)

# Model has them, DB doesn't → add columns via raw SQL with IF NOT EXISTS
print(f"Model has all {len(NEW_FIELDS)} fields, DB is missing {len(missing_in_db)}:")
for f in missing_in_db:
    print(f"   • {f}")

if input("\nAdd these columns via ALTER TABLE? [y/N] ").strip().lower() != "y":
    print("Aborted.")
    sys.exit(0)

with connection.cursor() as cur:
    for f in missing_in_db:
        cur.execute(f'ALTER TABLE subscriptions_plan ADD COLUMN IF NOT EXISTS "{f}" boolean NOT NULL DEFAULT true')
        print(f"   ✅ Added {f}")

# 4. Verify
print("\n" + "=" * 62)
print("✔️  VERIFICATION")
print("=" * 62)
with connection.cursor() as cur:
    cur.execute("""
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'subscriptions_plan'
    """)
    db_cols_after = {row[0] for row in cur.fetchall()}

still_missing = [f for f in NEW_FIELDS if f not in db_cols_after]
if still_missing:
    print(f"❌ Still missing: {still_missing}")
    sys.exit(1)

print(f"✅ All {len(NEW_FIELDS)} fields present in DB")
print("\n💡 To prevent recurrence: also record this in Django's state by editing")
print("   the migration that should have added these columns — or create a new migration")
print("   with `SeparateDatabaseAndState` if you want a full cleanup. For now the column")
print("   exists and Django can read/write it, so the endpoint will work.")