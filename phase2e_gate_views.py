"""Phase 2E: gate accounting views behind has_full_accounting."""
import os, sys, re, py_compile

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

# ── 1. Rewrite permissions.py with anonymous pass-through + superuser bypass ──
PERM_PATH = "subscriptions/permissions.py"
PERM_SRC = '''"""Phase 2A/2E - feature-flag enforcement helpers.

Rules:
  - Anonymous users pass through (so @login_required can redirect them).
  - Superusers always pass (so admins can test gated features).
  - Everyone else is checked against their tenant's plan flags.
"""
from functools import wraps
from django.http import JsonResponse
from rest_framework.permissions import BasePermission


class FeatureNotAvailable(Exception):
    """Raised when the current plan doesn't include the required feature."""
    def __init__(self, feature):
        self.feature = feature
        super().__init__(f"Plan does not include {feature}")


def user_can(request, feature: str) -> bool:
    """Return True if the current user may use the given plan feature."""
    user = getattr(request, "user", None)

    # Anonymous - let the view's own @login_required handle the redirect
    if user is None or not getattr(user, "is_authenticated", False):
        return True

    # Superusers bypass all gates (admin testing)
    if getattr(user, "is_superuser", False):
        return True

    plan = getattr(request, "tenant_plan", None)
    return bool(plan and getattr(plan, feature, False))


def requires_plan_feature(feature: str):
    """Plain-Django decorator - returns 402 Payment Required if flag is False.

    Anonymous users pass through so that @login_required (if present) can
    redirect them to login instead of showing a 402.
    """
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            user = getattr(request, "user", None)
            if user is not None and getattr(user, "is_authenticated", False):
                if not user_can(request, feature):
                    return JsonResponse(
                        {"error": "feature_not_available", "feature": feature,
                         "message": "This feature is not included in your plan. "
                                    "Upgrade to access it."},
                        status=402,
                    )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class HasPlanFeature(BasePermission):
    """DRF permission class - reads `required_feature` from the view."""
    message = "This feature is not included in your plan."

    def has_permission(self, request, view):
        feature = getattr(view, "required_feature", None)
        if not feature:
            return True
        if not request.user or not request.user.is_authenticated:
            return False
        return user_can(request, feature)
'''

with open(PERM_PATH, "w", encoding="utf-8") as f:
    f.write(PERM_SRC)
print(f"✅ Rewrote {PERM_PATH} (anon pass-through + superuser bypass)")

try:
    py_compile.compile(PERM_PATH, doraise=True)
    print(f"✅ {PERM_PATH} compiles cleanly")
except py_compile.PyCompileError as e:
    print(f"❌ {PERM_PATH} syntax error: {e}"); sys.exit(1)


# ── 2. Gate the views ──────────────────────────────────────────────────
GATES = {
    "accounting/views.py": {
        "accounts_list":      "has_full_accounting",
        "trial_balance":      "has_full_accounting",
        "balance_sheet":      "has_full_accounting",
        "income_statement":   "has_full_accounting",
        "journals_list":      "has_full_accounting",
        "general_ledger":     "has_full_accounting",
        "expenses_list":      "has_full_accounting",
        "expense_accounts":   "has_full_accounting",
    },
    "reports/views.py": {
        "cash_flow_statement": "has_full_accounting",
    },
}

IMPORT_LINE = "from subscriptions.permissions import requires_plan_feature"


def gate_file(path, gates):
    print(f"\n📄 {path}")
    if not os.path.exists(path):
        print(f"  ⚠️  file not found"); return

    with open(path, encoding="utf-8") as f:
        src = f.read()

    # 2a. Ensure the import is present
    if IMPORT_LINE not in src:
        lines = src.split("\n")
        last_import = 0
        for i, line in enumerate(lines):
            if line.startswith(("import ", "from ")):
                last_import = i
        lines.insert(last_import + 1, IMPORT_LINE)
        src = "\n".join(lines)
        print(f"  ✅ Added import")
    else:
        print(f"  ℹ️  import already present")

    lines = src.split("\n")
    insertions = []

    for func_name, feature in gates.items():
        found = False
        for i, line in enumerate(lines):
            if re.match(rf"^def {func_name}\s*\(", line):
                found = True
                insert_at = i
                while insert_at > 0:
                    prev = lines[insert_at - 1]
                    if prev.startswith("@"):
                        insert_at -= 1
                    elif prev.strip() == "":
                        break
                    else:
                        break

                already = any(
                    f'requires_plan_feature("{feature}")' in lines[j]
                    for j in range(insert_at, i)
                )
                if already:
                    print(f"  ℹ️  {func_name} already gated")
                else:
                    insertions.append((insert_at,
                                       f'@requires_plan_feature("{feature}")'))
                    print(f"  ✅ Will gate {func_name} -> {feature}")
                break
        if not found:
            print(f"  ⚠️  def {func_name}( not found")

    if not insertions:
        print(f"  ℹ️  no changes to apply")
        return

    # Insert bottom-up so indices don't shift
    insertions.sort(reverse=True)
    for idx, text in insertions:
        lines.insert(idx, text)

    new_src = "\n".join(lines)
    with open(path, "w", encoding="utf-8") as f:
        f.write(new_src)

    try:
        py_compile.compile(path, doraise=True)
        print(f"  ✅ {path} compiles cleanly")
    except py_compile.PyCompileError as e:
        print(f"  ❌ {path} syntax error: {e}"); sys.exit(1)


for path, gates in GATES.items():
    gate_file(path, gates)

print("\n" + "=" * 62)
print("🎉 Phase 2E complete")
print("=" * 62)
print("""
Next steps:

1.  Restart your Django server (decorator changes need reload):
        Ctrl+C, then:  python manage.py runserver

2.  As a Basic-tier user, visit:
        http://localhost:8000/accounting/trial-balance/
    →  should return JSON 402 with "feature_not_available"

3.  As a superuser, the same URL should work (bypass active).

4.  Upgrade that tenant to Professional in admin, log out/in, retry
    →  should serve the real HTML page.

Then we move to Phase 2F (end-to-end test).
""")