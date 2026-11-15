from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F
from django.contrib.auth import get_user_model
from tenants.models import Branch
from subscriptions.models import TenantUsage, Subscription

@receiver(pre_save, sender=Branch)
def enforce_branch_limit(sender, instance, **kwargs):
    # NOTE: Branch uses UUID pk with a default, so instance.pk is populated
    # BEFORE save. Use _state.adding to detect unsaved instances reliably.
    if instance._state.adding:
        with transaction.atomic():
            usage, _ = TenantUsage.objects.select_for_update().get_or_create(company=instance.company)
            try:
                sub = Subscription.objects.get(company=instance.company)
                if sub.plan.max_branches != -1 and usage.current_branches >= sub.plan.max_branches:
                    raise ValidationError(f"Limit reached: Plan allows {sub.plan.max_branches} branches.")
            except Subscription.DoesNotExist:
                pass # Handle if no subscription exists yet

@receiver(post_save, sender=Branch)
def update_branch_usage(sender, instance, created, **kwargs):
    if created:
        TenantUsage.objects.filter(company=instance.company).update(current_branches=F('current_branches') + 1)

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
