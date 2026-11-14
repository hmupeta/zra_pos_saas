from django.urls import path
from . import views

urlpatterns = [
    path("momo/initiate/", views.initiate_momo_payment, name="initiate_momo_payment"),
    path("momo/status/<str:reference_id>/", views.check_payment_status, name="check_payment_status"),
    path("delete-gateway/", views.delete_gateway, name="delete_gateway"),
    path("test-connection/", views.test_gateway_connection, name="test_gateway_connection"),
    path("mtn/generate-user/", views.generate_mtn_api_user, name="generate_mtn_api_user"),
    path("wallets/", views.tenant_wallets, name="tenant_wallets"),
    path("initiate/", views.initiate_momo, name="initiate_momo"),
    path("configs/", views.payment_configs, name="payment_configs"),
    path("webhook/", views.momo_webhook, name="momo_webhook"),
]
