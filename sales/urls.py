from django.urls import path
from . import views

urlpatterns = [
    path("quotations/<int:pk>/", views.quotation_detail, name="quotation_detail"),
    path("reservations/", views.reservations_list, name="reservations_list"),
    path("reservations/<int:pk>/cancel/", views.cancel_reservation, name="cancel_reservation"),
    path("reservations/<int:pk>/convert/", views.convert_reservation, name="convert_reservation"),
    path("quotations/", views.quotations_list, name="quotations_list"),
    path("quotations/<int:pk>/convert/", views.convert_quotation, name="convert_quotation"),
    path("shifts/<int:pk>/reconcile/", views.reconcile_shift, name="reconcile_shift"),
    path("shift/summary/", views.shift_summary, name="shift_summary"),
    path("agent-targets/", views.agent_targets, name="agent_targets"),
    path("shifts/", views.shifts_list, name="shifts_list"),
    path("shifts/<int:pk>/", views.shift_details, name="shift_details"),
    path("cart/discount/", views.apply_cart_discount, name="apply_cart_discount"),
    path("invoices/void/", views.void_invoice, name="void_invoice"),
    path("open-shift/", views.open_shift, name="open_shift"),
    path("close-shift/", views.close_shift, name="close_shift"),
    path("current-shift/", views.current_shift, name="current_shift"),
    path("scan-add/", views.scan_add, name="scan_add"),
    path("cart/", views.get_cart, name="get_cart"),
    path("cart/clear/", views.cart_clear, name="cart_clear"),
    path("cart/customer/", views.update_cart_customer, name="update_cart_customer"),
    path("cart/customer/", views.update_cart_customer, name="update_cart_customer"),
    path("cart/checkout/", views.checkout, name="checkout"),
    path("invoices/", views.invoices_list, name="invoices_list"),
    path("invoices/<int:invoice_id>/receipt.txt", views.receipt_text, name="receipt_text"),
]
