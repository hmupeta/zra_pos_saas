from django.urls import path
from . import views

urlpatterns = [
    path('search/', views.search_invoice, name='search_invoice'),
    path('invoice/<int:pk>/', views.invoice_details, name='invoice_details'),
    path('process/', views.process_return, name='process_return'),
]