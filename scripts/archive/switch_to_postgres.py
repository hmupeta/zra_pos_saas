"""
============================================================
SWITCH SQLITE → POSTGRESQL
============================================================
Usage:
    python switch_to_postgres.py

Before running:
  1. PostgreSQL is installed and running
  2. Database 'zra_pos_saas' and user 'pos_user' exist
     (see Step 3 of the guide)
"""

import os
import re
import sys
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
SETTINGS_FILE = BACKEND_PATH / "pos_backend" / "settings.py"
SQLITE_FILE = BACKEND_PATH / "db.sqlite3"


def get_python():
    venv = BACKEND_PATH / "venv"
    if platform.system() == "Windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def main():
    print("=" * 60)
    print("  SWITCH SQLITE → POSTGRESQL")
    print("=" * 60)
    print()

    # ------------------------------------------------------------------
    # 1. Check psycopg2
    # ------------------------------------------------------------------
    python = get_python()
    result = subprocess.run(
        [str(python), "-c", "import psycopg2; print(psycopg2.__version__)"],
        capture_output=True, text=True,
    )
    if result.returncode != 0:
        print("Installing psycopg2-binary...")
        subprocess.run(
            [str(python), "-m", "pip", "install", "psycopg2-binary", "--quiet"],
            check=True,
        )
        print("  [OK] psycopg2 installed")
    else:
        print(f"  [OK] psycopg2 {result.stdout.strip()}")
    print()

    # ------------------------------------------------------------------
    # 2. Get credentials
    # ------------------------------------------------------------------
    print("Enter PostgreSQL connection details:")
    db_name = input("  Database name    [zra_pos_saas]: ").strip() or "zra_pos_saas"
    db_user = input("  Database user    [pos_user]: ").strip() or "pos_user"
    db_pass = input("  Password         [Stacy2026!]: ").strip() or "Stacy2026!"
    db_host = input("  Host             [localhost]: ").strip() or "localhost"
    db_port = input("  Port             [5432]: ").strip() or "5432"
    print()

    # ------------------------------------------------------------------
    # 3. Test connection BEFORE touching anything
    # ------------------------------------------------------------------
    print("Testing connection...")
    try:
        import psycopg2
        conn = psycopg2.connect(
            dbname=db_name, user=db_user, password=db_pass,
            host=db_host, port=db_port, connect_timeout=5,
        )
        conn.close()
        print("  [OK] Connected to PostgreSQL")
    except Exception as e:
        print(f"  [ERROR] Cannot connect: {e}")
        print()
        print("  Fix this before continuing. Common causes:")
        print("    - PostgreSQL is not running (Get-Service postgresql*)")
        print("    - Database '{}' does not exist".format(db_name))
        print("    - User '{}' does not exist or wrong password".format(db_user))
        print("    - pg_hba.conf does not allow password auth from localhost")
        print()
        print("  Create the database with:")
        print("    psql -U postgres")
        print(f"    CREATE DATABASE {db_name};")
        print(f"    CREATE USER {db_user} WITH PASSWORD '{db_pass}';")
        print(f"    GRANT ALL PRIVILEGES ON DATABASE {db_name} TO {db_user};")
        print(f"    ALTER DATABASE {db_name} OWNER TO {db_user};")
        sys.exit(1)
    print()

    # ------------------------------------------------------------------
    # 4. Backup settings.py
    # ------------------------------------------------------------------
    backup = SETTINGS_FILE.with_suffix(".py.bak")
    if not backup.exists():
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            original = f.read()
        with open(backup, "w", encoding="utf-8") as f:
            f.write(original)
        print(f"  [OK] Backup: {backup.name}")
    else:
        print(f"  [SKIP] Backup already exists: {backup.name}")
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            original = f.read()
    print()

    # ------------------------------------------------------------------
    # 5. Replace DATABASES block
    # ------------------------------------------------------------------
    new_block = f'''DATABASES = {{
    "default": {{
        "ENGINE": "django.db.backends.postgresql",
        "NAME": "{db_name}",
        "USER": "{db_user}",
        "PASSWORD": "{db_pass}",
        "HOST": "{db_host}",
        "PORT": "{db_port}",
        "OPTIONS": {{
            "connect_timeout": 10,
        }},
        "CONN_MAX_AGE": 60,
        "ATOMIC_REQUESTS": False,
    }}
}}'''

    # Match "DATABASES = { ... }" — greedy up to the closing brace at column 0
    pattern = r"^DATABASES\s*=\s*\{.*?^\}"
    patched, count = re.subn(
        pattern, new_block, original, count=1, flags=re.MULTILINE | re.DOTALL,
    )

    if count == 0:
        print("  [ERROR] Could not find 'DATABASES = {...}' block in settings.py")
        print(f"          Open {SETTINGS_FILE} manually and replace the DATABASES block.")
        sys.exit(1)

    with open(SETTINGS_FILE, "w", encoding="utf-8", newline="\n") as f:
        f.write(patched)
    print("  [OK] settings.py updated to use PostgreSQL")
    print()

    # ------------------------------------------------------------------
    # 6. Run migrations
    # ------------------------------------------------------------------
    print("Running migrations on PostgreSQL...")
    print()
    result = subprocess.run(
        [str(python), "manage.py", "migrate"], cwd=BACKEND_PATH,
    )
    if result.returncode != 0:
        print()
        print("  [ERROR] Migration failed.")
        print(f"          Restore with: copy {backup.name} {SETTINGS_FILE.name}")
        sys.exit(1)
    print()
    print("  [OK] Migrations applied")
    print()

    # ------------------------------------------------------------------
    # 7. Seed data
    # ------------------------------------------------------------------
    ans = input("Run fix_seed.py to seed fresh data? [Y/n]: ").strip().lower()
    if ans in ("", "y", "yes"):
        seed_file = BACKEND_PATH / "fix_seed.py"
        if seed_file.exists():
            subprocess.run([str(python), "fix_seed.py"], cwd=BACKEND_PATH)
        else:
            print("  [SKIP] fix_seed.py not found — run it manually afterward")
    print()

    # ------------------------------------------------------------------
    # 8. Verify
    # ------------------------------------------------------------------
    print("=" * 60)
    print("  VERIFICATION")
    print("=" * 60)
    print()

    verify = subprocess.run(
        [str(python), "manage.py", "shell", "-c", """
from django.conf import settings
from django.contrib.auth import authenticate, get_user_model
from django.db import connection
from django.db.utils import OperationalError

engine = settings.DATABASES['default']['ENGINE']
print(f"  Engine: {engine}")

try:
    with connection.cursor() as c:
        c.execute("SELECT version()")
        version = c.fetchone()[0]
    print(f"  Server: {version.split(',')[0]}")
except OperationalError as e:
    print(f"  [FAIL] DB query failed: {e}")
    exit(1)

try:
    U = get_user_model()
    print(f"  Users: {U.objects.count()}")
    print(f"  Tenants: {__import__('core.models', fromlist=['Tenant']).Tenant.objects.count()}")
    owner = authenticate(username='demo_owner', password='Demo@123456')
    print(f"  demo_owner login: {'OK' if owner else 'FAIL'}")
    admin = authenticate(username='admin', password='Admin@123456')
    print(f"  admin login: {'OK' if admin else 'FAIL'}")
except Exception as e:
    print(f"  [WARN] {e}")
        """],
        cwd=BACKEND_PATH, capture_output=True, text=True,
    )
    print(verify.stdout)
    if verify.stderr.strip():
        print(verify.stderr)
    print()

    # ------------------------------------------------------------------
    # 9. SQLite backup
    # ------------------------------------------------------------------
    if SQLITE_FILE.exists():
        ans = input("Keep SQLite backup? (rename to db.sqlite3.bak) [Y/n]: ").strip().lower()
        if ans in ("", "y", "yes"):
            bak = BACKEND_PATH / "db.sqlite3.bak"
            if bak.exists():
                bak.unlink()
            SQLITE_FILE.rename(bak)
            print(f"  [OK] Renamed to {bak.name}")

    print()
    print("=" * 60)
    print("  ✅ MIGRATION TO POSTGRESQL COMPLETE")
    print("=" * 60)
    print()
    print(f"  DB:   {db_name} @ {db_host}:{db_port}")
    print(f"  User: {db_user}")
    print()
    print("  Start the server:")
    print("    python manage.py runserver")
    print()
    print("  Revert to SQLite if needed:")
    print(f"    copy pos_backend\\settings.py.bak pos_backend\\settings.py")
    print(f"    move db.sqlite3.bak db.sqlite3")
    print()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nCancelled.")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n[ERROR] {e}\n")
        traceback.print_exc()
        sys.exit(1)