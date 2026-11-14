


from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import SystemNotification

@receiver(post_save, sender="inventory.Product")
def check_low_stock(sender, instance, **kwargs):
    """Trigger an alert when stock falls below reorder level."""
    if instance.current_stock <= instance.reorder_level and instance.is_active:
        today = timezone.now().date()
        # Check if we already alerted about this today to prevent spam
        exists = SystemNotification.objects.filter(
            tenant=instance.tenant,
            title="Low Stock Alert",
            message__contains=instance.name,
            created_at__date=today
        ).exists()
        
        if not exists:
            SystemNotification.objects.create(
                tenant=instance.tenant,
                title="Low Stock Alert",
                message=f"{instance.name} is running low. Only {instance.current_stock} left (Reorder level: {instance.reorder_level}).",
                notification_type="WARNING",
                link="/products"
            )

@receiver(post_save, sender="zra_integration.ZRASubmission")
def check_zra_failure(sender, instance, created, **kwargs):
    """Trigger an alert if a ZRA submission fails."""
    if instance.status == "FAILED":
        SystemNotification.objects.create(
            tenant=instance.invoice.tenant,
            title="ZRA Submission Failed",
            message=f"Invoice {instance.invoice.invoice_number} failed to submit to ZRA. Please retry.",
            notification_type="ERROR",
            link="/zra-compliance"
        )
