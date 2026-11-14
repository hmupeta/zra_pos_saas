from django.urls import path
from . import views

urlpatterns = [
    path("cash-flow/", views.cash_flow_statement, name="cash_flow_statement"),
    path("zra-tax/", views.zra_tax_summary, name="zra_tax_summary"),
    path("sales-by-category/", views.sales_by_category, name="sales_by_category"),
    path("agent-performance/", views.agent_performance, name="agent_performance"),
    path("sales-summary/", views.sales_summary, name="sales_summary"),
    path("dashboard/", views.dashboard, name="dashboard"),
]
