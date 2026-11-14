from django.db import models


class ZRASubmission(models.Model):
    invoice = models.ForeignKey("sales.Invoice", on_delete=models.CASCADE, related_name="zra_submissions")
    status = models.CharField(max_length=20, default="PENDING")
    validation_code = models.CharField(max_length=100, blank=True)
    qr_code = models.TextField(blank=True)
    receipt_number = models.CharField(max_length=100, blank=True)
    error_message = models.TextField(blank=True)
    response_data = models.JSONField(default=dict, blank=True)
    submitted_at = models.DateTimeField(auto_now_add=True)
