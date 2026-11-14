#!/usr/bin/env python
"""
pre_phase2_setup.py
===================
Runs all pre-Phase-2 housekeeping in one shot:

  1. Back up the database (Postgres / SQLite auto-detected)
  2. Initialize git (if needed) and commit current state
  3. Archive one-off root scripts into scripts/archive/
  4. Seed a test Company + Basic Subscription
  5. Assign first company-less superuser to that tenant
  6. Add /api/subscriptions/entitlements/ endpoint

Safe to re-run. Each step prints ✅ / ℹ️ / ⚠️ / ❌.
"""
import os
import re
import sys
import glob
import shutil
import subprocess
from datetime import datetime

# ----------------------------------------------------------------------
def log(icon, msg):
    print(f"{icon}  {msg}")

def run(cmd, env=None, check=True):
    printable = " ".join(cmd) if isinstance(cmd, list) else cmd
    log("⚙️ ", printable)
    try:
        r = subprocess.run(cmd, shell=isinstance(cmd, str),
                           check=check, env=env, text=True,
                           capture_output=True)
        return r
    except FileNotFoundError as e:
        log("❌", f"Not found: {e}")
        raise
    except subprocess.CalledProcessError as e:
        log("❌", f"Failed: {printable}")
        if e.stderr:
            print(e.stderr)
        raise

def read(p):
    with open(p, "r", encoding="utf-8") as f:
        return f.read()

def write(p, c):
    os.makedirs(os.path.dirname(p) or ".", exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        f.write(c)

# ----------------------------------------------------------------------
# Bootstrap Django
# ----------------------------------------------------------------------
if not os.path.exists("manage.py"):
    log("❌", "Run this from the project root (where manage.py lives).")
    sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django
django.setup()
from django.conf import settings as dj_settings
log("✅", "Django loaded")

# ======================================================================
# STEP 1 — Database backup
# ======================================================================
def backup_db():
    log("📦", "STEP 1 — Database backup")
    db = dj_settings.DATABASES["default"]
    engine = db["ENGINE"].rsplit(".", 1)[-1]
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    os.makedirs("backups", exist_ok=True)

    if engine == "postgresql":
        out = f"backups/db_phase1_{stamp}.dump"
        env = os.environ.copy()
        if db.get("PASSWORD"):
            env["PGPASSWORD"] = db["PASSWORD"]
        try:
            run([
                "pg_dump",
                "-U", db["USER"] or "postgres",
                "-h", db.get("HOST") or "localhost",
                "-p", str(db.get("PORT") or 5432),
                "-d", db["NAME"],
                "-F", "c",
                "-f", out,
            ], env=env)
            size = os.path.getsize(out) // 1024
            log("✅", f"Postgres backup → {out} ({size} KB)")
        except FileNotFoundError:
            log("⚠️ ", "pg_dump not on PATH — skipping DB backup. Add PostgreSQL bin/ to PATH and rerun.")
        except subprocess.CalledProcessError:
            log("⚠️ ", "pg_dump failed — check credentials in settings.py.")
    elif engine == "sqlite3":
        out = f"backups/db_phase1_{stamp}.sqlite3"
        shutil.copy2(db["NAME"], out)
        log("✅", f"SQLite backup → {out}")
    else:
        log("⚠️ ", f"Unrecognised engine '{engine}' — back up manually.")

backup_db()

# ======================================================================
# STEP 2 — Git init + commit
# ======================================================================
def git_setup():
    log("\n🌳", "STEP 2 — Version control")
    if not shutil.which("git"):
        log("⚠️ ", "git not installed — skipping.")
        return

    if not os.path.isdir(".git"):
        run(["git", "init"])
        run(["git", "branch", "-M", "main"])
        log("✅", "git initialized on branch 'main'")
    else:
        log("ℹ️ ", ".git already present")

    if not os.path.exists(".gitignore"):
        write(".gitignore", """\
__pycache__/
*.py[cod]
venv/
.venv/
.env
media/
staticfiles/
logs/
backups/
*.sqlite3
*.sqlite3.bak
.DS_Store
.vscode/
.idea/
""")
        log("✅", "Created .gitignore")

    run(["git", "add", "."])
    status = subprocess.run(["git", "status", "--porcelain"],
                            capture_output=True, text=True).stdout.strip()
    if status:
        run(["git", "commit", "-m",
             "Phase 1 complete: multi-tenant foundation + subscription tiers"])
        log("✅", "Git commit created")
    else:
        log("ℹ️ ", "Working tree clean — nothing to commit")

git_setup()

# ======================================================================
# STEP 3 — Archive one-off scripts
# ======================================================================
def archive_scripts():
    log("\n🗂️ ", "STEP 3 — Archive one-off scripts")
    archive_dir = "scripts/archive"
    os.makedirs(archive_dir, exist_ok=True)

    patterns = [
        "add_*.py", "fix_*.py", "force_*.py", "beautify_*.py",
        "enhance_*.py", "rebuild_*.py", "expand_*.py", "ultimate_*.py",
        "upgrade_*.py", "wire_*.py", "inject_*.py", "restore_*.py",
        "switch_*.py", "implement_*.py", "verify_*.py", "ix_*.py",
    ]
    moved = 0
    for pat in patterns:
        for f in glob.glob(pat):
            target = os.path.join(archive_dir, f)
            if os.path.exists(target):
                continue  # don't clobber already-archived
            shutil.move(f, target)
            moved += 1

    log("✅" if moved else "ℹ️ ",
        f"Archived {moved} script(s) into {archive_dir}/" if moved
        else "No unarchived scripts to move")

archive_scripts()

# ======================================================================
# STEP 4 — Seed test tenant
# ======================================================================
def seed_test_tenant():
    log("\n🏢", "STEP 4 — Seed test tenant")
    from tenants.models import Company
    from subscriptions.models import Plan, Subscription, TenantUsage

    company, created = Company.objects.get_or_create(
        tpin="TEST0000001",
        defaults={"name": "Test Shop Ltd"},
    )
    log("✅" if created else "ℹ️ ",
        f"Created {company.name}" if created
        else f"Already exists: {company.name}")

    basic = Plan.objects.get(name="Basic")
    sub, created = Subscription.objects.get_or_create(
        company=company,
        defaults={"plan": basic, "is_active": True},
    )
    log("✅" if created else "ℹ️ ",
        f"Subscribed → {basic.name}" if created
        else f"Already subscribed → {sub.plan.name}")

    TenantUsage.objects.get_or_create(company=company)
    return company

test_company = seed_test_tenant()

# ======================================================================
# STEP 5 — Assign first company-less superuser
# ======================================================================
def assign_admin(company):
    log("\n👤", "STEP 5 — Assign admin to test tenant")
    from core.models import User

    if not hasattr(User, "company"):
        log("⚠️ ", "core.User has no 'company' field — skipping (add the FK first)")
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
    log("\n🔌", "STEP 6 — /api/subscriptions/entitlements/ endpoint")

    # --- 6a: subscriptions/views.py ---
    views_path = "subscriptions/views.py"
    content = read(views_path) if os.path.exists(views_path) else ""

    required_imports = [
        "from rest_framework.views import APIView",
        "from rest_framework.response import Response",
        "from rest_framework.permissions import IsAuthenticated",
    ]
    for imp in required_imports:
        if imp not in content:
            content = imp + "\n" + content

    view_body = '''
class TenantEntitlementsView(APIView):
    """Returns the current tenant's plan limits + live usage.
    Used by the frontend to hide/disable 'Add Branch' / 'Invite User' buttons."""
    permission_classes = [IsAuthenticated]

    def get(self, request):
        plan = getattr(request, "tenant_plan", None)
        usage = getattr(request, "tenant_usage", None)
        if not plan or not usage:
            return Response({"detail": "No subscription found"}, status=404)
        return Response({
            "plan_name": plan.name,
            "limits": {
                "max_branches": plan.max_branches,
                "max_users": plan.max_users,
            },
            "usage": {
                "current_branches": usage.current_branches,
                "current_users": usage.current_users,
            },
            "can_add_branch": plan.max_branches == -1 or usage.current_branches < plan.max_branches,
            "can_add_user": plan.max_users == -1 or usage.current_users < plan.max_users,
        })
'''
    if "TenantEntitlementsView" not in content:
        write(views_path, content.rstrip() + "\n\n" + view_body.strip() + "\n")
        log("✅", f"Added TenantEntitlementsView to {views_path}")
    else:
        log("ℹ️ ", "TenantEntitlementsView already present")

    # --- 6b: subscriptions/urls.py ---
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
            write(urls_path, u.rstrip() + '\nurlpatterns += [path("entitlements/", TenantEntitlementsView.as_view(), name="tenant-entitlements")]\n')
            log("✅", f"Appended entitlements/ route to {urls_path}")
        else:
            log("ℹ️ ", f"{urls_path} already has entitlements/")

    # --- 6c: pos_backend/urls.py (safe append, not regex) ---
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
    write(root_urls, rc.rstrip() + "\n" + injection)
    log("✅", f"Wired subscriptions.urls into {root_urls}")

add_entitlements_endpoint()

# ======================================================================
# DONE
# ======================================================================
log("\n" + "=" * 60, "")
log("🎉", "All pre-Phase-2 steps complete!")
log("=" * 60, "")
print("""
Next actions:

  1.  Check git status:     git log --oneline -1
  2.  Verify endpoint:      python manage.py shell
                              >>> from django.urls import reverse
                              >>> reverse('tenant-entitlements')
                              '/api/subscriptions/entitlements/'
  3.  Start server:         python manage.py runserver
  4.  Manual smoke test:    log in as admin → GET /api/subscriptions/entitlements/
                            (expect JSON with plan "Basic", can_add_branch: true until 1 branch exists)

Ready for Phase 2 (Core POS + ZRA Integration)! 🚀
""")