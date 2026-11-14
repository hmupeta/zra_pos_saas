from django.urls import path
from . import views

urlpatterns = [path("email-receipt/", views.email_receipt, name="email_receipt")]
