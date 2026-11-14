from django.urls import path
from . import views

urlpatterns = [
    path('', views.customers_list, name='customers_list'),
    path('pos-search/', views.customer_search_pos, name='customer_search_pos'),
]