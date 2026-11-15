"""Phase 2A: add feature flags to Plan + decorator for views + seed."""
import os, sys

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()

# ── 1. Append missing fields to subscriptions/models.py ─────────────────
MODELS = "subscriptions/models.py"
with open(MODELS, "r", encoding="utf-8") as f:
    content = f.read()

MARKER = "# Phase 2A feature flags"
if MARKER in content:
    print("ℹ️  Plan already extended — skipping model edit")
else:
    # Insert new fields right before __str__
    anchor = "    def __str__(self):\n        return self.name"
    new_fields = """    # Phase 2A feature flags
    has_pos                  = models.BooleanField(default=True)
    has_inventory            = models.BooleanField(default=True)
    has_zra_smart_invoice    = models.BooleanField(default=True)
    has_full_accounting      = models.BooleanField(default=False)
    has_dedicated_manager    = models.BooleanField(default=False)
    has_custom_sla           = models.BooleanField(default=False)

    def has(self, feature: str) -> bool:
        \"\"\"Convenience helper: plan.has('has_full_accounting')\"\"\"
        return bool(getattr(self, feature, False))

"""
    if anchor in content:
        content = content.replace(anchor, new_fields + anchor, 1)
        with open(MODELS, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"✅ Added 6 new flags + has() helper to {MODELS}")
    else:
        print("❌ Could not locate Plan.__str__ anchor — inspect subscriptions/models.py manually")
        sys.exit(1)

# ── 2. Create the decorator / permission file ───────────────────────────
os.makedirs("subscriptions", exist_ok=True)
write = lambda p, c: open(p, "w", encoding="utf-8").write(c.strip() + "\n")

write("subscriptions/permissions.py", '''
"""Phase 2A — feature-flag enforcement helpers.

Usage in DRF views:
    class MyView(APIView):
        permission_classes = [IsAuthenticated, HasPlanFeature]
        required_feature = "has_full_accounting"

Usage in plain Django views:
    from subscriptions.permissions import requires_plan_feature

    @requires_plan_feature("has_api_access")
    def my_view(request): ...
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
    plan = getattr(request, "tenant_plan", None)
    return bool(plan and getattr(plan, feature, False))


def requires_plan_feature(feature: str):
    """Plain-Django decorator — returns 402 Payment Required if flag is False."""
    def decorator(view_func):
        @wraps(view_func)
        def wrapper(request, *args, **kwargs):
            if not user_can(request, feature):
                return JsonResponse(
                    {"error": "feature_not_available", "feature": feature,
                     "message": "Upgrade your plan to access this feature."},
                    status=402,
                )
            return view_func(request, *args, **kwargs)
        return wrapper
    return decorator


class HasPlanFeature(BasePermission):
    """DRF permission class — reads `required_feature` from the view."""
    message = "This feature is not included in your plan."

    def has_permission(self, request, view):
        feature = getattr(view, "required_feature", None)
        if not feature:
            return True  # view didn't opt in — allow (auth still applies)
        return user_can(request, feature)
''')
print("✅ Created subscriptions/permissions.py")

# ── 3. Migrate ──────────────────────────────────────────────────────────
from django.core.management import call_command
print("\n⚙️  Running makemigrations subscriptions...")
call_command("makemigrations", "subscriptions", verbosity=1)
print("⚙️  Running migrate...")
call_command("migrate", verbosity=0)
print("✅ Migrations applied")

# ── 4. Reseed plans with the new flags ──────────────────────────────────
from subscriptions.models import Plan

PLANS = [
    {"name": "Basic", "price_zmw": 500,
     "max_branches": 1, "max_users": 5,
     "has_api_access": False, "has_multi_branch_reports": False,
     "has_pos": True, "has_inventory": True, "has_zra_smart_invoice": True,
     "has_full_accounting": False,
     "has_dedicated_manager": False, "has_custom_sla": False},
    {"name": "Professional", "price_zmw": 1500,
     "max_branches": 5, "max_users": 25,
     "has_api_access": True, "has_multi_branch_reports": True,
     "has_pos": True, "has_inventory": True, "has_zra_smart_invoice": True,
     "has_full_accounting": True,
     "has_dedicated_manager": False, "has_custom_sla": False},
    {"name": "Enterprise", "price_zmw": 0,
     "max_branches": -1, "max_users": -1,
     "has_api_access": True, "has_multi_branch_reports": True,
     "has_pos": True, "has_inventory": True, "has_zra_smart_invoice": True,
     "has_full_accounting": True,
     "has_dedicated_manager": True, "has_custom_sla": True},
]

print()
for p in PLANS:
    name = p.pop("name")
    obj, created = Plan.objects.update_or_create(name=name, defaults=p)
    print(f"{'✅' if created else '🔄'} {name}: "
          f"{'created' if created else 'updated'}")

# ── 5. Bump Plan into the entitlements endpoint response ────────────────
VIEWS = "subscriptions/views.py"
vc = open(VIEWS, "r", encoding="utf-8").read()
if '"features"' not in vc and "features" not in vc.split("TenantEntitlementsView")[-1][:600]:
    vc = vc.replace(
        '"plan_name": plan.name,',
        '''"plan_name": plan.name,
            "features": {
                "has_pos": plan.has("has_pos"),
                "has_inventory": plan.has("has_inventory"),
                "has_zra_smart_invoice": plan.has("has_zra_smart_invoice"),
                "has_full_accounting": plan.has("has_full_accounting"),
                "has_multi_branch_reports": plan.has("has_multi_branch_reports"),
                "has_api_access": plan.has("has_api_access"),
                "has_dedicated_manager": plan.has("has_dedicated_manager"),
                "has_custom_sla": plan.has("has_custom_sla"),
            },''',
        1,
    )
    open(VIEWS, "w", encoding="utf-8").write(vc)
    print(f"✅ Added features block to {VIEWS}")
else:
    print("ℹ️  Entitlements endpoint already returns features")

print("\n" + "=" * 60)
print("🎉 Phase 2A complete")
print("=" * 60)
print("""
Verify:
  python manage.py shell -c "from subscriptions.models import Plan; [print(p.name, '|', p.has_full_accounting, '|', p.has_api_access) for p in Plan.objects.all()]"
""")