from django.urls import path
from . import views

urlpatterns = [
    path("products/template/", views.download_product_template, name="download_product_template"),
    path("products/import/", views.import_products_csv, name="import_products_csv"),
    path("transfers/", views.transfers_list, name="transfers_list"),
    path('stocktakes/', views.stocktakes_list, name='stocktakes_list'),
    path('stocktakes/<int:pk>/', views.stocktake_detail, name='stocktake_detail'),
    path('stocktakes/<int:pk>/scan/', views.stocktake_scan, name='stocktake_scan'),
    path('stocktakes/<int:pk>/submit/', views.stocktake_submit, name='stocktake_submit'),
    path('stocktakes/<int:pk>/approve/', views.stocktake_approve, name='stocktake_approve'),
    path('products/', views.products_list, name='products_list'),
    path('products/receive/', views.receive_stock, name='receive_stock'),
    path('products/barcode/<str:barcode>/', views.product_by_barcode, name='product_by_barcode'),
    path('categories/', views.categories_list, name='categories'),
    path('tax-rates/', views.tax_rates_list, name='tax_rates'),
    path('low-stock/', views.low_stock_products, name='low_stock'),
]