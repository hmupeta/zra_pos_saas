import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add Expense Model
# ============================================================
models_path = BACKEND_PATH / "accounting" / "models.py"
content = models_path.read_text(encoding="utf-8")

if "class Expense" not in content:
    content += '''

class Expense(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    date = models.DateField()
    account = models.ForeignKey(Account, on_delete=models.PROTECT, help_text="Expense category (e.g. Rent, Utilities)")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_method = models.CharField(max_length=50, default="CASH")
    reference = models.CharField(max_length=100, blank=True)
    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey("core.User", on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.account.name} - {self.amount}"
'''
    models_path.write_text(content, encoding="utf-8")
print("✅ Added Expense model")

# ============================================================
# 2. Add Expense Views (with Auto-Accounting)
# ============================================================
views_path = BACKEND_PATH / "accounting" / "views.py"
content = views_path.read_text(encoding="utf-8")

expense_views = '''
from .models import Expense
from django.utils import timezone
import datetime

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def expenses_list(request):
    if request.method == "GET":
        qs = Expense.objects.filter(tenant=request.tenant).order_by("-date")
        return Response([{
            "id": e.id, "date": e.date.strftime("%Y-%m-%d"),
            "account": e.account.name, "amount": float(e.amount),
            "payment_method": e.payment_method, "reference": e.reference
        } for e in qs])

    # POST: Create Expense
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER", "ACCOUNTANT"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    amount = Decimal(str(data.get("amount", 0)))
    account_id = data.get("account_id")
    payment_method = data.get("payment_method", "CASH")
    ref = data.get("reference", "")

    try:
        expense_account = Account.objects.get(id=account_id, tenant=request.tenant)
    except Account.DoesNotExist:
        return Response({"error": "Invalid expense account"}, status=400)

    # Determine credit account (Cash vs Bank)
    credit_code = "1000" if payment_method == "CASH" else "1010"
    credit_account = Account.objects.filter(tenant=request.tenant, code=credit_code).first()
    
    if not credit_account:
        return Response({"error": f"Missing system account: {credit_code}"}, status=400)

    # 1. Save Expense
    expense = Expense.objects.create(
        tenant=request.tenant, company=request.branch,
        date=data.get("date", timezone.now().date()),
        account=expense_account, amount=amount,
        payment_method=payment_method, reference=ref,
        notes=data.get("notes", ""), recorded_by=request.user
    )

    # 2. Auto-Post Journal
    journal = Journal.objects.create(
        tenant=request.tenant, company=request.branch,
        journal_number=f"EXP-{expense.id}", date=expense.date,
        description=f"Expense: {expense_account.name} - {ref}",
        journal_type="GENERAL", status="POSTED", created_by=request.user
    )
    
    # Debit Expense, Credit Cash/Bank
    JournalLine.objects.create(journal=journal, account=expense_account, debit=amount, description=f"Paid {expense_account.name}")
    JournalLine.objects.create(journal=journal, account=credit_account, credit=amount, description=f"Paid via {payment_method}")

    return Response({"success": True, "id": expense.id})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def expense_accounts(request):
    # Only return accounts that are classified as EXPENSE
    accounts = Account.objects.filter(tenant=request.tenant, account_type="EXPENSE", is_header=False)
    return Response([{"id": a.id, "name": a.name, "code": a.code} for a in accounts])
'''

if "def expenses_list" not in content:
    views_path.write_text(content + "\n\n" + expense_views, encoding="utf-8")
print("✅ Added Expense views")

# ============================================================
# 3. Update URLs
# ============================================================
urls_path = BACKEND_PATH / "accounting" / "urls.py"
urls_content = urls_path.read_text(encoding="utf-8")
if "expenses_list" not in urls_content:
    urls_content = urls_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path("expenses/", views.expenses_list, name="expenses_list"),
    path("expenses/accounts/", views.expense_accounts, name="expense_accounts"),'''
    )
    urls_path.write_text(urls_content, encoding="utf-8")
print("✅ Updated accounting/urls.py")

# ============================================================
# 4. Add Frontend Route and Navigation
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")
if "def expenses_page" not in web_content:
    web_content += "\n\ndef expenses_page(request):\n    return render(request, 'pos/expenses.html')\n"
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/expenses" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('expenses', views_web.expenses_page, name='expenses_page'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")
if "href=\"/expenses\"" not in nav_content:
    # Place it under Purchasing
    nav_content = nav_content.replace(
        '<a href="/purchasing" class="nav-link"',
        '<a href="/expenses" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)">Expenses</a>\n    <a href="/purchasing" class="nav-link"'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Expenses to Sidebar")

# ============================================================
# 5. Create Expenses UI (HTML)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "expenses.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Expenses{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="expensesApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Operational Expenses</h1>
      <button @click="showModal = true" class="btn-primary">+ Record Expense</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Date</th>
            <th class="px-4 py-3">Expense Account</th>
            <th class="px-4 py-3">Paid Via</th>
            <th class="px-4 py-3">Reference</th>
            <th class="px-4 py-3 text-right">Amount</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="e in expenses" :key="e.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3" x-text="e.date"></td>
              <td class="px-4 py-3 font-medium text-brand-700" x-text="e.account"></td>
              <td class="px-4 py-3"><span class="bg-gray-100 px-2 py-0.5 rounded text-xs" x-text="e.payment_method"></span></td>
              <td class="px-4 py-3 text-gray-500" x-text="e.reference || '-'"></td>
              <td class="px-4 py-3 text-right font-bold text-red-600" x-text="'- ' + formatCurrency(e.amount)"></td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="expenses.length === 0" class="p-8 text-center text-gray-400">No expenses recorded yet.</div>
    </div>

    <!-- New Expense Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4">Record Expense</h2>
          <form @submit.prevent="createExpense()" class="space-y-3">
            
            <div>
              <label class="block text-sm mb-1">Expense Category (Account)</label>
              <select x-model="form.account_id" class="input-field" required>
                <option value="">Select Account...</option>
                <template x-for="a in accounts" :key="a.id">
                  <option :value="a.id" x-text="a.code + ' - ' + a.name"></option>
                </template>
              </select>
            </div>

            <div>
              <label class="block text-sm mb-1">Amount (K)</label>
              <input type="number" step="0.01" x-model="form.amount" class="input-field" required>
            </div>

            <div>
              <label class="block text-sm mb-1">Paid Via</label>
              <select x-model="form.payment_method" class="input-field">
                <option value="CASH">Cash (Drawer)</option>
                <option value="BANK">Bank Transfer</option>
                <option value="MOMO">Mobile Money</option>
              </select>
            </div>

            <div>
              <label class="block text-sm mb-1">Reference / Description</label>
              <input type="text" x-model="form.reference" placeholder="e.g. ZESCO Bill #123" class="input-field">
            </div>

            <button type="submit" class="btn-primary w-full mt-4">Save Expense</button>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function expensesApp() {
  return {
    expenses: [], accounts: [], showModal: false,
    form: { account_id: '', amount: '', payment_method: 'CASH', reference: '' },

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        this.expenses = await apiFetch('/accounting/expenses/');
        this.accounts = await apiFetch('/accounting/expenses/accounts/');
      } catch (e) { alert(e.message); }
    },

    async createExpense() {
      try {
        await apiFetch('/accounting/expenses/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        this.form = { account_id: '', amount: '', payment_method: 'CASH', reference: '' };
        this.load();
      } catch (e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created expenses.html UI")

# ============================================================
# 6. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "accounting"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")