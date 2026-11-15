"""Sales signals — ZRA invoice compliance guard."""
from django.db.models.signals import pre_save
from django.dispatch import receiver
from django.core.exceptions import ValidationError
from sales.models import Invoice


@receiver(pre_save, sender=Invoice)
def enforce_zra_compliance(sender, instance, **kwargs):
    """Block transition to PAID if fiscalization has not been attempted.

    Rules enforced:
      - status='PAID' requires zra_status in (SUBMITTED, OFFLINE_QUEUED)
      - zra_status='SUBMITTED' requires zra_receipt_number
    """
    # Determine if this save transitions TO PAID
    if instance.pk:
        try:
            old_status = Invoice.objects.only("status").get(pk=instance.pk).status
        except Invoice.DoesNotExist:
            old_status = None
    else:
        old_status = None

    if instance.status == "PAID" and old_status != "PAID":
        if instance.zra_status not in ("SUBMITTED", "OFFLINE_QUEUED"):
            raise ValidationError(
                f"Invoice cannot be marked PAID: ZRA status is "
                f"'{instance.zra_status}'. Submit to VSDC first, or queue "
                f"offline (zra_status='OFFLINE_QUEUED')."
            )

    if instance.zra_status == "SUBMITTED" and not instance.zra_receipt_number:
        raise ValidationError(
            "zra_status='SUBMITTED' requires zra_receipt_number to be set."
        )
