#!/usr/bin/env python
"""
pre_phase2_resume.py
====================
Resumes pre-Phase-2 setup after the first run crashed at Step 4.

Does ONLY what's left:
  1. Retry DB backup with auto-detected pg_dump path
  2. Seed test tenant (TPIN = 10 chars)
  3. Assign admin
  4. Add entitlements endpoint
  5. Final git commit
"""
import os
import sys
import glob
import shutil
import subprocess
from datetime import datetime

if not os.path.exists("manage.py"):
    print("❌ Run this from project root (where manage.py lives).")
    sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django
django.setup()
from django.conf import settings as dj_settings

def log(icon, msg):
    print(f"{icon}  {msg}")

def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def write(p, c):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(c)

# ======================================================================
# STEP 1 (retry) — Find pg_dump and back up
# ======================================================================
def find_pg_dump():
    p = shutil.which("pg_dump")
    if p:
        return p
    patterns = [
        r"C:\Program Files\PostgreSQL\*\bin\pg_dump.exe",
        r"C:\Program Files (x86)\PostgreSQL\*\bin\pg_dump.exe",
        r"C:\PostgreSQL\*\bin\pg_dump.exe",
        r"C:\ProgramData\chocolatey\lib\postgresql*\tools\pgsql\bin\pg_dump.exe",
    ]
    found = []
    for pat in patterns:
        found.extend(glob.glob(pat))
    if not found:
        return None
    # Prefer newest version (numeric sort on version folder)
    found.sort(reverse=True)
    return found[0]

def backup_db():
    log("📦", "STEP 1 (retry) — Database backup")
    db = dj_settings.DATABASES["default"]
    if "postgresql" not in db["ENGINE"]:
        log("ℹ️ ", f"Engine is {db['ENGINE']} — skipping pg_dump")
        return

    pg_dump = find_pg_dump()
    if not pg_dump:
        log("❌", "pg_dump.exe not found anywhere. Install PostgreSQL client tools or add bin/ to PATH.")
        return
    log("✅", f"Found pg_dump: {pg_dump}")

    os.makedirs("backups", exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = f"backups/db_phase1_{stamp}.dump"

    env = os.environ.copy()
    if db.get("PASSWORD"):
        env["PGPASSWORD"] = db["PASSWORD"]

    cmd = [
        pg_dump,
        "-U", db["USER"] or "postgres",
        "-h", db.get("HOST") or "localhost",
        "-p", str(db.get("PORT") or 5432),
        "-d", db["NAME"],
        "-F", "c",
        "-f", out,
    ]
    log("⚙️ ", " ".join(cmd))
    try:
        subprocess.run(cmd, env=env, capture_output=True, text=True, check=True)
        size = os.path.getsize(out) // 1024
        log("✅", f"Backup → {out} ({size} KB)")
    except subprocess.CalledProcessError as e:
        log("❌", f"pg_dump failed: {e.stderr.strip()[:300]}")
        log("💡", "Check DB_USER / DB_PASSWORD in .env or pos_backend/settings.py")

backup_db()

# ======================================================================
# STEP 4 — Seed test tenant (FIXED: 10-char TPIN)
# ======================================================================
def seed_test_tenant():
    log("\n🏢", "STEP 4 — Seed test tenant")
    from tenants.models import Company
    from subscriptions.models import Plan, Subscription, TenantUsage

    TEST_TPIN = "TEST000001"  # exactly 10 chars

    company, created = Company.objects.get_or_create(
        tpin=TEST_TPIN,
        defaults={"name": "Test Shop Ltd"},
    )
    log("✅" if created else "ℹ️ ",
        f"Company: {company.name}" if created else f"Already exists: {company.name}")

    basic = Plan.objects.get(name="Basic")
    sub, created = Subscription.objects.get_or_create(
        company=company,
        defaults={"plan": basic, "is_active": True},
    )
    log("✅" if created else "ℹ️ ",
        f"Subscribed → {basic.name}" if created else f"Already subscribed → {sub.plan.name}")

    TenantUsage.objects.get_or_create(company=company)
    return company

test_company = seed_test_tenant()

# ======================================================================
# STEP 5 — Assign admin
# ======================================================================
def assign_admin(company):
    log("\n👤", "STEP 5 — Assign admin to test tenant")
    from core.models import User

    if not hasattr(User, "company"):
        log("⚠️ ", "core.User has no 'company' field — skipping.")
        return

    orphans = User.objects.filter(is_superuser=True, company__isnull=True)
    if not orphans.exists():
        log("ℹ️ ", "No company-less superusers — nothing to assign")
        return
    for u in orphans:
        u.company = company
        u.save(update_fields=["company"])
        log("✅", f"{u.username} → {company.name}")

assign_admin(test_company)

# ======================================================================
# STEP 6 — Entitlements endpoint
# ======================================================================
def add_entitlements_endpoint():
    log("\n🔌", "STEP 6 — /api/subscriptions/entitlements/")

    # --- views.py ---
    views_path = "subscriptions/views.py"
    content = read(views_path) if os.path.exists(views_path) else ""

    for imp in [
        "from rest_framework.views import APIView",
        "from rest_framework.response import Response",
        "from rest_framework.permissions import IsAuthenticated",
    ]:
        if imp not in content:
            content = imp + "\n" + content

    if "TenantEntitlementsView" not in content:
        content += '''

class TenantEntitlementsView(APIView):
    """Returns current tenant's plan limits + live usage.
    Frontend uses this to hide/disable 'Add Branch' / 'Invite User' buttons."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plan = getattr(request, "tenant_plan", None)
        usage = getattr(request, "tenant_usage", None)
        if not plan or not usage:
            return Response({"detail": "No subscription found"}, status=404)
        return Response({
            "plan_name": plan.name,
            "limits": {"max_branches": plan.max_branches, "max_users": plan.max_users},
            "usage": {"current_branches": usage.current_branches, "current_users": usage.current_users},
            "can_add_branch": plan.max_branches == -1 or usage.current_branches < plan.max_branches,
            "can_add_user": plan.max_users == -1 or usage.current_users < plan.max_users,
        })
'''
        write(views_path, content)
        log("✅", f"Added TenantEntitlementsView to {views_path}")
    else:
        log("ℹ️ ", "TenantEntitlementsView already present")

    # --- subscriptions/urls.py ---
    urls_path = "subscriptions/urls.py"
    if not os.path.exists(urls_path):
        write(urls_path, """\
from django.urls import path
from .views import TenantEntitlementsView

urlpatterns = [
    path("entitlements/", TenantEntitlementsView.as_view(), name="tenant-entitlements"),
]
""")
        log("✅", f"Created {urls_path}")
    else:
        u = read(urls_path)
        if "entitlements/" not in u:
            write(urls_path, u.rstrip() + '\n\nurlpatterns += [\n    path("entitlements/", TenantEntitlementsView.as_view(), name="tenant-entitlements"),\n]\n')
            log("✅", f"Appended entitlements/ route to {urls_path}")
        else:
            log("ℹ️ ", f"{urls_path} already wired")

    # --- pos_backend/urls.py ---
    root_urls = "pos_backend/urls.py"
    if not os.path.exists(root_urls):
        log("⚠️ ", f"{root_urls} not found — wire subscriptions.urls manually")
        return

    marker = "# -- Phase 2: subscriptions --"
    rc = read(root_urls)
    if marker in rc:
        log("ℹ️ ", f"{root_urls} already wired")
        return

    injection = f"""

{marker}
from django.urls import path as _ph_path, include as _ph_inc
from subscriptions import urls as _sub_urls
urlpatterns += [_ph_path("api/subscriptions/", _ph_inc(_sub_urls))]
"""
    write(root_urls, rc.rstrip() + injection)
    log("✅", f"Wired subscriptions.urls into {root_urls}")

add_entitlements_endpoint()

# ======================================================================
# STEP 7 — Final commit
# ======================================================================
def final_commit():
    log("\n🌳", "STEP 7 — Final commit")
    if not os.path.isdir(".git") or not shutil.which("git"):
        log("ℹ️ ", "No git repo — skipping")
        return
    subprocess.run(["git", "add", "."], check=False)
    st = subprocess.run(["git", "status", "--porcelain"],
                        capture_output=True, text=True).stdout.strip()
    if not st:
        log("ℹ️ ", "Nothing to commit")
        return
    subprocess.run(
        ["git", "commit", "-m",
         "Phase 1 polish: entitlements endpoint + test tenant seeded"],
        check=False,
    )
    log("✅", "Committed")

final_commit()

# ======================================================================
print("\n" + "=" * 60)
log("🎉", "Pre-Phase-2 setup finished!")
print("=" * 60)
print("""
Verify now:

  1. git log --oneline -3
     → you should see at least 2 Phase-1 commits

  2. python manage.py shell -c "from django.urls import reverse; print(reverse('tenant-entitlements'))"
     → /api/subscriptions/entitlements/

  3. python manage.py shell -c "from tenants.models import Company; print(list(Company.objects.values_list('name','tpin')))"
     → [('Test Shop Ltd', 'TEST000001')]

  4. python manage.py runserver
     Then GET /api/subscriptions/entitlements/ (with auth header)

Ready for Phase 2! 🚀
""")