from django.urls import path
from .views import TenantEntitlementsView

urlpatterns = [
    path("entitlements/", TenantEntitlementsView.as_view(), name="tenant-entitlements"),
]
