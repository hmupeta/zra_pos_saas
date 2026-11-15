from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('', include('core.urls_web')),
    path("admin/", admin.site.urls),
    path("api/auth/", include("core.urls")),
    path("api/saas/", include("saas.urls")),
    path("api/inventory/", include("inventory.urls")),
    path("api/sales/", include("sales.urls")),
    path("api/customers/", include("customers.urls")),
    path("api/payments/", include("payments.urls")),
    path("api/zra/", include("zra_integration.urls")),
    path("api/returns/", include("returns.urls")),
    path("api/notifications/", include("notifications.urls")),
    path("api/reports/", include("reports.urls")),
    path("api/purchasing/", include("purchasing.urls")),
    path("api/accounting/", include("accounting.urls")),
]

# -- Phase 2: subscriptions --
from django.urls import path as _ph_path, include as _ph_inc
from subscriptions import urls as _sub_urls
urlpatterns += [_ph_path("api/subscriptions/", _ph_inc(_sub_urls))]

# Serve static and media files during local development
if settings.DEBUG:
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)