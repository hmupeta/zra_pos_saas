from django.urls import path
from . import views

urlpatterns = [
    path("notifications/", views.get_notifications, name="get_notifications"),
    path("notifications/read/", views.mark_notifications_read, name="mark_notifications_read"),
    path("branches/manage/", views.branches_manage, name="branches_manage"),
    path("export/products/", views.export_products, name="export_products"),
    path("export/invoices/", views.export_invoices, name="export_invoices"),
    path("export/customers/", views.export_customers, name="export_customers"),
    path("barcode/<str:barcode_num>/", views.generate_barcode_image, name="generate_barcode"),
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("me/", views.me, name="me"),
    path("branches/", views.branches_list, name="branches_list"),
    path("branches/switch/", views.switch_branch, name="switch_branch"),
    path("health/", views.health, name="health"),
    path("users/", views.users_list_create, name="users_list_create"),
    path("company/", views.company_settings, name="company_settings"),
]