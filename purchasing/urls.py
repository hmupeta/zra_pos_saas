from django.urls import path
from . import views

urlpatterns = [
    path('po/', views.purchase_orders_list, name='purchase_orders_list'),
    path('po/<int:pk>/', views.po_details, name='po_details'),
    path('po/<int:pk>/receive/', views.receive_po, name='receive_po'),
    path('suppliers/', views.suppliers_list, name='suppliers_list'),
    path('invoices/', views.supplier_invoices, name='supplier_invoices'),
    path('invoices/create/', views.create_invoice, name='create_invoice'),
    path('pay/', views.pay_supplier, name='pay_supplier'),
]