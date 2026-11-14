from django.urls import path
from . import views, billing_views

urlpatterns = [
    path("admin/gateways/", views.platform_gateways, name="platform_gateways"),
    path("admin/billing/invoices/", views.platform_invoices, name="platform_invoices"),
    path("admin/billing/payments/", views.platform_payments, name="platform_payments"),
    # Platform admin routes
    path("admin/dashboard/", billing_views.admin_dashboard, name="admin_dashboard"),
    path("admin/tenants/", billing_views.admin_tenants, name="admin_tenants"),
    
    # Public routes
    path("plans/", views.list_plans, name="plans"),
    path("signup/", views.submit_signup, name="signup"),
]