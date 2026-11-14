from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import (
    User, Tenant, Company, Device, BranchAccess,
    SubscriptionPlan, AuditLog, LoginHistory,
)


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "email", "tenant", "user_type", "employment_status", "is_active")
    list_filter = ("user_type", "employment_status", "tenant")
    fieldsets = UserAdmin.fieldsets + (
        ("SaaS", {"fields": ("tenant", "user_type", "employment_status", "phone_number")}),
    )


@admin.register(Tenant)
class TenantAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "plan", "subscription_status", "is_active")
    list_filter = ("subscription_status", "plan")
    search_fields = ("code", "name", "contact_email")


@admin.register(Company)
class CompanyAdmin(admin.ModelAdmin):
    list_display = ("name", "tenant", "branch_code", "tpin", "is_active")
    list_filter = ("tenant", "is_active")


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = ("device_id", "company", "is_active", "last_sync")


@admin.register(SubscriptionPlan)
class PlanAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "monthly_price_zmw", "max_branches", "max_users")


admin.site.register(BranchAccess)
admin.site.register(AuditLog)
admin.site.register(LoginHistory)
