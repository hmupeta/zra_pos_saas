from django.contrib import admin
from .models import SignupApplication, TenantInvite


@admin.register(SignupApplication)
class SignupApplicationAdmin(admin.ModelAdmin):
    list_display = ("business_name", "contact_email", "plan", "status", "submitted_at")
    list_filter = ("status", "plan")
    search_fields = ("business_name", "contact_email", "contact_phone")


@admin.register(TenantInvite)
class TenantInviteAdmin(admin.ModelAdmin):
    list_display = ("email", "tenant", "user_type", "status", "expires_at")
    list_filter = ("status", "tenant")
