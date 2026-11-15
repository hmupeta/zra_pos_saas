"""Adds user-seat enforcement to subscriptions/signals.py (idempotent)."""
import os, sys

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

SIGNALS_PATH = "subscriptions/signals.py"
MARKER = "# --- User seat enforcement (Phase 1 completion) ---"

with open(SIGNALS_PATH, "r", encoding="utf-8") as f:
    content = f.read()

if MARKER in content:
    print("ℹ️  User limit signal already installed — nothing to do")
    sys.exit(0)

# Add the missing import at the top
if "from django.contrib.auth import get_user_model" not in content:
    content = content.replace(
        "from tenants.models import Branch",
        "from django.contrib.auth import get_user_model\nfrom tenants.models import Branch"
    )

user_signals = '''

# --- User seat enforcement (Phase 1 completion) ---
User = get_user_model()


@receiver(pre_save, sender=User)
def enforce_user_limit(sender, instance, **kwargs):
    """Block new user creation when the tenant is at its seat limit."""
    if instance.pk:
        return  # only enforce on creation
    if not getattr(instance, "company_id", None):
        return  # no tenant assigned — nothing to enforce
    with transaction.atomic():
        usage, _ = TenantUsage.objects.select_for_update().get_or_create(
            company_id=instance.company_id
        )
        try:
            sub = Subscription.objects.get(company_id=instance.company_id)
        except Subscription.DoesNotExist:
            return  # unsubscribed tenant — let it through (or block, your call)
        if sub.plan.max_users != -1 and usage.current_users >= sub.plan.max_users:
            raise ValidationError(
                f"Limit reached: Plan allows {sub.plan.max_users} users. "
                f"Upgrade your subscription to add more."
            )


@receiver(post_save, sender=User)
def update_user_usage(sender, instance, created, **kwargs):
    if created and getattr(instance, "company_id", None):
        TenantUsage.objects.filter(company_id=instance.company_id).update(
            current_users=F("current_users") + 1
        )
'''

with open(SIGNALS_PATH, "w", encoding="utf-8") as f:
    f.write(content.rstrip() + user_signals)

print(f"✅ Patched {SIGNALS_PATH} with user limit signal")
print("⚠️  Restart any running Django server to reload the signal.")