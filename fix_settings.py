import re

SETTINGS_PATH = "pos_backend/settings.py"

with open(SETTINGS_PATH, "r", encoding="utf-8") as f:
    content = f.read()

changed = False

# 1. Inject tenants + subscriptions BEFORE "core" (order matters!)
if '"tenants"' not in content:
    content = content.replace(
        '    "core",',
        '    "tenants",\n    "subscriptions",\n    "core",',
        1,
    )
    changed = True
    print("✅ Injected 'tenants' and 'subscriptions' before 'core'")
else:
    print("ℹ️  'tenants' already in INSTALLED_APPS — skipping")

# 2. Inject the tenant middleware after AuthenticationMiddleware
if "TenantLimitMiddleware" not in content:
    content = content.replace(
        '"django.contrib.auth.middleware.AuthenticationMiddleware",',
        '"django.contrib.auth.middleware.AuthenticationMiddleware",\n    "subscriptions.middleware.TenantLimitMiddleware",',
        1,
    )
    changed = True
    print("✅ Injected TenantLimitMiddleware")
else:
    print("ℹ️  TenantLimitMiddleware already present — skipping")

if changed:
    with open(SETTINGS_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"\n💾 Saved {SETTINGS_PATH}")
else:
    print("\n🎉 Settings already correct — nothing to do")