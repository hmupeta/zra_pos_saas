from django.shortcuts import render, redirect


def index(request):
    return redirect("/welcome")


def login_page(request):
    return render(request, "pos/login.html")


def branch_select_page(request):
    return render(request, "pos/branch_select.html")


def pos_page(request):
    return render(request, "pos/pos.html")


def dashboard_page(request):
    return render(request, "pos/dashboard.html")


def products_page(request):
    return render(request, "pos/products.html")


def invoices_page(request):
    return render(request, "pos/invoices.html")


def reports_page(request):
    return render(request, "pos/reports.html")


def settings_page(request):
    return render(request, "pos/settings.html")


def admin_dashboard_page(request):
    return render(request, "pos/admin/dashboard.html")


def admin_applications_page(request):
    return render(request, "pos/admin/applications.html")


def admin_tenants_page(request):
    return render(request, "pos/admin/tenants.html")


def admin_plans_page(request):
    return render(request, "pos/admin/plans.html")


def admin_billing_page(request):
    return render(request, "pos/admin/billing.html")


def users_page(request):
    return render(request, 'pos/users.html')


def coa_page(request):
    return render(request, "pos/accounting_coa.html")

def journals_page(request):
    return render(request, "pos/accounting_journals.html")

def ledger_page(request):
    return render(request, "pos/accounting_ledger.html")


def stocktake_page(request):
    return render(request, 'pos/stocktake.html')


def purchasing_page(request):
    return render(request, 'pos/purchasing.html')


def customers_page(request):
    return render(request, 'pos/customers.html')


def expenses_page(request):
    return render(request, 'pos/expenses.html')


def returns_page(request):
    return render(request, 'pos/returns.html')


def tax_rates_page(request):
    return render(request, 'pos/tax_rates.html')


def categories_page(request):
    return render(request, 'pos/categories.html')


def landing_page(request):
    return render(request, "pos/landing.html")

def terms_page(request):
    return render(request, "pos/terms.html")


def barcodes_page(request):
    return render(request, 'pos/barcodes.html')


def shifts_page(request):
    return render(request, 'pos/shifts.html')


def transfers_page(request):
    return render(request, 'pos/transfers.html')


def platform_dashboard_page(request):
    return render(request, "pos/platform_dashboard.html")

def platform_tenants_page(request):
    return render(request, "pos/platform_tenants.html")

def platform_applications_page(request):
    return render(request, "pos/platform_applications.html")


def platform_billing_page(request):
    return render(request, 'pos/platform_billing.html')


def platform_gateways_page(request):
    return render(request, 'pos/platform_gateways.html')

def tenant_wallets_page(request):
    return render(request, 'pos/wallets.html')


def branches_page(request):
    return render(request, 'pos/branches.html')


def commissions_page(request):
    return render(request, 'pos/commissions.html')


def quotations_page(request):
    return render(request, 'pos/quotations.html')


def reservations_page(request):
    return render(request, 'pos/reservations.html')

def invoice_detail_page(request, pk):
    return render(request, "pos/invoice_detail.html", {"invoice_id": pk})
