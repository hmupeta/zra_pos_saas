from django.db import models


class NotificationLog(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE, null=True, blank=True)
    channel = models.CharField(max_length=20)
    recipient = models.CharField(max_length=200)
    subject = models.CharField(max_length=255, blank=True)
    message = models.TextField()
    status = models.CharField(max_length=20, default="QUEUED")
    error = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
