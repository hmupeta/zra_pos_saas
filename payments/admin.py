from django.contrib import admin
from .models import BranchPaymentConfig, PaymentTransaction


@admin.register(BranchPaymentConfig)
class ConfigAdmin(admin.ModelAdmin):
    list_display = ("branch", "provider", "is_default", "is_enabled")


admin.site.register(PaymentTransaction)
