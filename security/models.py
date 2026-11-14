from django.db import models


class PasswordResetToken(models.Model):
    user = models.ForeignKey("core.User", on_delete=models.CASCADE)
    token = models.CharField(max_length=100, unique=True)
    expires_at = models.DateTimeField()
    used = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
