from django.urls import path
from . import views

urlpatterns = [path("submit/", views.submit_invoice, name="submit_zra")]
