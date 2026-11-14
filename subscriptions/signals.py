from django.db.models.signals import pre_save, post_save
from django.dispatch import receiver
from django.db import transaction
from django.core.exceptions import ValidationError
from django.db.models import F
from tenants.models import Branch
from subscriptions.models import TenantUsage, Subscription

@receiver(pre_save, sender=Branch)
def enforce_branch_limit(sender, instance, **kwargs):
    if not instance.pk:
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
