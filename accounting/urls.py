from django.urls import path
from . import views

urlpatterns = [
    path("expenses/", views.expenses_list, name="expenses_list"),
    path("expenses/accounts/", views.expense_accounts, name="expense_accounts"),
    path("accounts/", views.accounts_list, name="accounts"),
    path("journals/", views.journals_list, name="journals"),
    path("ledger/<int:account_id>/", views.general_ledger, name="general_ledger"),
    path("reports/trial-balance/", views.trial_balance, name="trial_balance"),
    path("reports/balance-sheet/", views.balance_sheet, name="balance_sheet"),
    path("reports/income-statement/", views.income_statement, name="income_statement"),
]