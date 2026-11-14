from pathlib import Path
import re

BACKEND_PATH = Path(__file__).resolve().parent
ACC_DIR = BACKEND_PATH / "accounting"

# ============================================================
# 1. Fix Account Model
# ============================================================
models_path = ACC_DIR / "models.py"
models_content = models_path.read_text(encoding="utf-8")

# Ensure the Account model has a correct balance() method
new_models = '''
from django.db import models
from django.conf import settings
from decimal import Decimal

class Account(models.Model):
    TYPES = [("ASSET", "Asset"), ("LIABILITY", "Liability"), ("EQUITY", "Equity"),
             ("REVENUE", "Revenue"), ("EXPENSE", "Expense")]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE, null=True, blank=True, related_name="accounts")
    code = models.CharField(max_length=20)
    name = models.CharField(max_length=200)
    account_type = models.CharField(max_length=20, choices=TYPES)
    is_header = models.BooleanField(default=False)
    is_control = models.BooleanField(default=False)
    opening_balance = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        ordering = ["code"]
        unique_together = [("tenant", "code")]

    def __str__(self):
        return f"{self.code} - {self.name}"

    @property
    def normal_balance(self):
        if self.account_type in ("ASSET", "EXPENSE"):
            return "DEBIT"
        return "CREDIT"

    def balance(self):
        from django.db.models import Sum
        agg = self.journal_lines.aggregate(dr=Sum("debit"), cr=Sum("credit"))
        dr, cr = agg["dr"] or Decimal("0"), agg["cr"] or Decimal("0")
        
        # We return the balance according to its normal side (positive = normal, negative = abnormal)
        if self.normal_balance == "DEBIT":
            return self.opening_balance + dr - cr
        else:
            return self.opening_balance + cr - dr


class Journal(models.Model):
    TYPES = [("SALES", "Sales"), ("PURCHASE", "Purchase"), ("GENERAL", "General"),
             ("ADJUSTMENT", "Adjustment")]
    STATUS = [("DRAFT", "Draft"), ("POSTED", "Posted"), ("VOID", "Void")]
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    company = models.ForeignKey("core.Company", on_delete=models.CASCADE)
    journal_number = models.CharField(max_length=50)
    date = models.DateField()
    description = models.TextField()
    journal_type = models.CharField(max_length=20, choices=TYPES, default="GENERAL")
    status = models.CharField(max_length=20, choices=STATUS, default="POSTED")
    source_invoice = models.ForeignKey("sales.Invoice", on_delete=models.SET_NULL, null=True, blank=True, related_name="journals")
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    posted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-date", "-id"]
        unique_together = [("tenant", "journal_number")]

    def total_debit(self):
        from django.db.models import Sum
        return self.lines.aggregate(t=Sum("debit"))["t"] or Decimal("0")

    def total_credit(self):
        from django.db.models import Sum
        return self.lines.aggregate(t=Sum("credit"))["t"] or Decimal("0")

    def is_balanced(self):
        return self.total_debit() == self.total_credit()


class JournalLine(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE, related_name="lines")
    account = models.ForeignKey(Account, on_delete=models.PROTECT, related_name="journal_lines")
    debit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    credit = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        side = "DR" if self.debit > 0 else "CR"
        amount = self.debit if self.debit > 0 else self.credit
        return f"{side} {self.account.code} - {amount}"
'''
models_path.write_text(new_models.strip(), encoding="utf-8")
print("✅ Updated accounting/models.py (Added normal_balance logic)")

# ============================================================
# 2. Fix Views (Trial Balance, Balance Sheet, Income Statement, Journals)
# ============================================================
views_path = ACC_DIR / "views.py"
new_views = '''
from datetime import date
from decimal import Decimal
from django.db.models import Sum
from django.utils import timezone
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import Account, Journal, JournalLine

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def accounts_list(request):
    qs = Account.objects.filter(tenant=request.tenant, is_active=True)
    return Response([{
        "id": a.id, "code": a.code, "name": a.name, "type": a.account_type,
        "balance": float(a.balance()),
    } for a in qs])

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def trial_balance(request):
    accounts = Account.objects.filter(tenant=request.tenant, is_active=True, is_header=False)
    rows = []
    total_dr, total_cr = Decimal("0"), Decimal("0")
    
    for a in accounts:
        bal = a.balance()
        if bal == 0:
            continue
            
        if a.normal_balance == "DEBIT":
            if bal > 0:
                total_dr += bal
                rows.append({"code": a.code, "name": a.name, "debit": float(bal), "credit": 0})
            else:
                total_cr += abs(bal)
                rows.append({"code": a.code, "name": a.name, "debit": 0, "credit": float(abs(bal))})
        else:
            if bal > 0:
                total_cr += bal
                rows.append({"code": a.code, "name": a.name, "debit": 0, "credit": float(bal)})
            else:
                total_dr += abs(bal)
                rows.append({"code": a.code, "name": a.name, "debit": float(abs(bal)), "credit": 0})

    return Response({
        "accounts": rows,
        "total_debit": float(total_dr),
        "total_credit": float(total_cr),
        "balanced": round(total_dr, 2) == round(total_cr, 2),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def balance_sheet(request):
    def sum_type(t):
        accounts = Account.objects.filter(tenant=request.tenant, account_type=t, is_header=False)
        return sum((a.balance() for a in accounts), Decimal("0"))
        
    assets = sum_type("ASSET")
    liabilities = sum_type("LIABILITY")
    equity = sum_type("EQUITY")
    revenue = sum_type("REVENUE")
    expenses = sum_type("EXPENSE")
    net_income = revenue - expenses
    
    return Response({
        "assets": float(assets),
        "liabilities": float(liabilities),
        "equity": float(equity),
        "net_income": float(net_income),
        "balanced": round(assets, 2) == round(liabilities + equity + net_income, 2),
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def income_statement(request):
    def sum_type(t):
        accounts = Account.objects.filter(tenant=request.tenant, account_type=t, is_header=False)
        return sum((a.balance() for a in accounts), Decimal("0"))
        
    revenue = sum_type("REVENUE")
    expenses = sum_type("EXPENSE")
    net_income = revenue - expenses
    margin = (net_income / revenue * 100) if revenue > 0 else 0
    
    return Response({
        "revenue": float(revenue),
        "expenses": float(expenses),
        "net_income": float(net_income),
        "margin_percent": float(margin),
    })

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def journals_list(request):
    if request.method == "GET":
        qs = Journal.objects.filter(tenant=request.tenant)
        return Response([{
            "id": j.id, "journal_number": j.journal_number, "date": j.date,
            "description": j.description, "journal_type": j.journal_type,
            "total": float(j.total_debit()), "is_balanced": j.is_balanced()
        } for j in qs[:100]])
        
    # POST: Create a new manual journal
    data = request.data
    lines = data.get("lines", [])
    
    if not lines:
        return Response({"error": "Journal must have lines"}, status=400)
        
    total_dr = sum(Decimal(str(l.get("debit", 0))) for l in lines)
    total_cr = sum(Decimal(str(l.get("credit", 0))) for l in lines)
    
    if total_dr != total_cr:
        return Response({"error": "Total debits must equal total credits"}, status=400)
        
    import datetime
    j_num = f"JV-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
    
    journal = Journal.objects.create(
        tenant=request.tenant, company=request.branch,
        journal_number=j_num, date=data.get("date", date.today()),
        description=data.get("description", "Manual Entry"),
        journal_type=data.get("journal_type", "GENERAL"),
        status="POSTED", created_by=request.user,
    )
    
    for line in lines:
        account = Account.objects.get(id=line["account_id"], tenant=request.tenant)
        JournalLine.objects.create(
            journal=journal, account=account,
            debit=Decimal(str(line.get("debit", 0))),
            credit=Decimal(str(line.get("credit", 0))),
            description=line.get("description", ""),
        )
        
    return Response({"success": True, "journal_id": journal.id})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def general_ledger(request, account_id):
    account = Account.objects.get(id=account_id, tenant=request.tenant)
    lines = JournalLine.objects.filter(account=account).select_related("journal").order_by("journal__date")
    
    running_bal = account.opening_balance
    entries = []
    
    for line in lines:
        if account.normal_balance == "DEBIT":
            running_bal += line.debit - line.credit
        else:
            running_bal += line.credit - line.debit
            
        entries.append({
            "date": line.journal.date.isoformat(),
            "reference": line.journal.journal_number,
            "description": line.description or line.journal.description,
            "debit": float(line.debit),
            "credit": float(line.credit),
            "balance": float(running_bal),
        })
        
    return Response({
        "account": {"code": account.code, "name": account.name, "type": account.account_type},
        "entries": entries
    })
'''
views_path.write_text(new_views.strip(), encoding="utf-8")
print("✅ Updated accounting/views.py (Fixed Trial Balance, Added Journal Entry API, Added General Ledger)")

# ============================================================
# 3. Fix Auto-Posting Signal
# ============================================================
signals_path = ACC_DIR / "signals.py"
new_signals = '''
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from sales.models import Invoice
from .models import Account, Journal, JournalLine

@receiver(post_save, sender=Invoice)
def auto_post_sale_journal(sender, instance, created, **kwargs):
    if instance.status != "PAID":
        return
    if instance.journals.filter(status="POSTED").exists():
        return
        
    tenant = instance.shift.company.tenant
    if not tenant:
        return
        
    cash = Account.objects.filter(tenant=tenant, code="1000").first()
    sales_acct = Account.objects.filter(tenant=tenant, code="4000").first()
    vat = Account.objects.filter(tenant=tenant, code="2100").first()
    
    if not all([cash, sales_acct, vat]):
        return
        
    journal = Journal.objects.create(
        tenant=tenant, company=instance.shift.company,
        journal_number=f"JV-{instance.invoice_number}",
        date=instance.created_at.date(),
        description=f"Sale {instance.invoice_number}",
        journal_type="SALES", status="POSTED",
        source_invoice=instance, created_by=instance.cashier,
    )
    
    # Debit Cash (Total)
    JournalLine.objects.create(journal=journal, account=cash, debit=instance.total)
    
    # Credit Sales (Net Subtotal)
    JournalLine.objects.create(journal=journal, account=sales_acct, credit=instance.subtotal)
    
    # Credit VAT (Tax)
    if instance.tax_total > 0:
        JournalLine.objects.create(journal=journal, account=vat, credit=instance.tax_total)
'''
signals_path.write_text(new_signals.strip(), encoding="utf-8")
print("✅ Updated accounting/signals.py (Ensuring Dr = Cr)")

# ============================================================
# 4. Update URLs
# ============================================================
urls_path = ACC_DIR / "urls.py"
new_urls = '''
from django.urls import path
from . import views

urlpatterns = [
    path("accounts/", views.accounts_list, name="accounts"),
    path("journals/", views.journals_list, name="journals"),
    path("ledger/<int:account_id>/", views.general_ledger, name="general_ledger"),
    path("reports/trial-balance/", views.trial_balance, name="trial_balance"),
    path("reports/balance-sheet/", views.balance_sheet, name="balance_sheet"),
    path("reports/income-statement/", views.income_statement, name="income_statement"),
]
'''
urls_path.write_text(new_urls.strip(), encoding="utf-8")
print("✅ Updated accounting/urls.py")

# ============================================================
# 5. Update Frontend Template (Reports)
# ============================================================
tpl_path = BACKEND_PATH / "templates" / "pos" / "reports.html"
new_tpl = '''
{% extends "pos/base.html" %}
{% block title %}Reports{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="reportsPage()" x-init="load('trial')">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Financial Reports</h1>
      <button @click="showJournalModal = true" class="btn-primary text-sm">+ Journal Entry</button>
    </div>

    <div class="flex gap-2 mb-6 border-b">
      <template x-for="t in tabs" :key="t.id">
        <button @click="load(t.id)"
                :class="tab === t.id ? 'text-brand-700 border-b-2 border-brand-600' : 'text-gray-500'"
                class="px-4 py-2 text-sm font-medium" x-text="t.label"></button>
      </template>
    </div>

    <!-- Trial Balance -->
    <div x-show="tab === 'trial' && data" class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Code</th>
            <th class="px-4 py-3">Account</th>
            <th class="px-4 py-3 text-right">Debit</th>
            <th class="px-4 py-3 text-right">Credit</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="a in data?.accounts || []" :key="a.code">
            <tr class="border-t hover:bg-gray-50 cursor-pointer" @click="loadLedger(a)">
              <td class="px-4 py-2 font-mono text-xs text-brand-600" x-text="a.code"></td>
              <td class="px-4 py-2" x-text="a.name"></td>
              <td class="px-4 py-2 text-right" x-text="a.debit > 0 ? formatCurrency(a.debit) : '-'"></td>
              <td class="px-4 py-2 text-right" x-text="a.credit > 0 ? formatCurrency(a.credit) : '-'"></td>
            </tr>
          </template>
          <tr class="border-t-2 bg-gray-50 font-bold">
            <td class="px-4 py-3" colSpan="2">Totals</td>
            <td class="px-4 py-3 text-right" x-text="formatCurrency(data?.total_debit)"></td>
            <td class="px-4 py-3 text-right" x-text="formatCurrency(data?.total_credit)"></td>
          </tr>
        </tbody>
      </table>
      <div x-show="data && !data.balanced" class="p-3 bg-red-50 text-red-700 text-sm font-bold">
        ⚠ Books are NOT balanced. Debits must equal Credits.
      </div>
    </div>

    <!-- Balance Sheet -->
    <div x-show="tab === 'balance' && data" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="card p-6">
        <h2 class="font-semibold mb-4 text-green-700">Assets</h2>
        <div class="text-2xl font-bold" x-text="formatCurrency(data?.assets)"></div>
      </div>
      <div class="card p-6">
        <h2 class="font-semibold mb-4">Liabilities & Equity</h2>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between"><span>Liabilities</span><span x-text="formatCurrency(data?.liabilities)"></span></div>
          <div class="flex justify-between"><span>Equity</span><span x-text="formatCurrency(data?.equity)"></span></div>
          <div class="flex justify-between"><span>Net Income</span><span x-text="formatCurrency(data?.net_income)"></span></div>
          <div class="flex justify-between border-t pt-2 font-bold mt-2">
            <span>Total Equity & Liabilities</span>
            <span x-text="formatCurrency((data?.liabilities||0) + (data?.equity||0) + (data?.net_income||0))"></span>
          </div>
        </div>
      </div>
    </div>

    <!-- Income Statement -->
    <div x-show="tab === 'income' && data" class="card p-6 max-w-xl">
      <div class="flex justify-between py-2 border-b"><span>Revenue</span><span class="font-semibold" x-text="formatCurrency(data?.revenue)"></span></div>
      <div class="flex justify-between py-2 border-b"><span>Expenses</span><span class="font-semibold" x-text="formatCurrency(data?.expenses)"></span></div>
      <div class="flex justify-between py-3 text-lg font-bold">
        <span>Net Income</span>
        <span :class="data?.net_income >= 0 ? 'text-green-700' : 'text-red-700'" x-text="formatCurrency(data?.net_income)"></span>
      </div>
      <div class="text-sm text-gray-500">Margin: <span x-text="(data?.margin_percent || 0).toFixed(1)"></span>%</div>
    </div>

    <!-- General Ledger Drill-down -->
    <template x-if="ledgerData">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-3xl w-full p-6 max-h-[90vh] flex flex-col">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold" x-text="'Ledger: ' + ledgerData?.account?.name + ' (' + ledgerData?.account?.code + ')'"></h2>
            <button @click="ledgerData = null" class="text-gray-500 hover:text-gray-800">✕</button>
          </div>
          <div class="flex-1 overflow-y-auto">
            <table class="w-full text-sm">
              <thead class="bg-gray-50 text-left text-xs uppercase">
                <tr><th class="px-4 py-2">Date</th><th class="px-4 py-2">Ref</th><th class="px-4 py-2">Description</th><th class="px-4 py-2 text-right">Debit</th><th class="px-4 py-2 text-right">Credit</th><th class="px-4 py-2 text-right">Balance</th></tr>
              </thead>
              <tbody>
                <template x-for="e in ledgerData?.entries || []" :key="e.reference">
                  <tr class="border-t">
                    <td class="px-4 py-2" x-text="e.date"></td>
                    <td class="px-4 py-2 text-xs" x-text="e.reference"></td>
                    <td class="px-4 py-2" x-text="e.description"></td>
                    <td class="px-4 py-2 text-right" x-text="e.debit > 0 ? formatCurrency(e.debit) : '-'"></td>
                    <td class="px-4 py-2 text-right" x-text="e.credit > 0 ? formatCurrency(e.credit) : '-'"></td>
                    <td class="px-4 py-2 text-right font-semibold" x-text="formatCurrency(e.balance)"></td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </template>

    <!-- Manual Journal Entry Modal -->
    <template x-if="showJournalModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-2xl w-full p-6">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">New Journal Entry</h2>
            <button @click="showJournalModal = false" class="text-gray-500 hover:text-gray-800">✕</button>
          </div>
          <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label class="block text-sm mb-1">Date</label>
              <input type="date" x-model="journalForm.date" class="input-field">
            </div>
            <div>
              <label class="block text-sm mb-1">Description</label>
              <input type="text" x-model="journalForm.description" placeholder="e.g. Paid Rent" class="input-field">
            </div>
          </div>
          
          <table class="w-full text-sm mb-4">
            <thead><tr><th class="text-left pb-2">Account</th><th class="text-right pb-2">Debit</th><th class="text-right pb-2">Credit</th></tr></thead>
            <tbody>
              <template x-for="(line, idx) in journalForm.lines" :key="idx">
                <tr>
                  <td class="pr-2">
                    <select x-model="line.account_id" class="input-field">
                      <option value="">Select Account...</option>
                      <template x-for="a in accounts" :key="a.id">
                        <option :value="a.id" x-text="a.code + ' - ' + a.name"></option>
                      </template>
                    </select>
                  </td>
                  <td class="pr-2"><input type="number" x-model="line.debit" class="input-field text-right" placeholder="0.00"></td>
                  <td><input type="number" x-model="line.credit" class="input-field text-right" placeholder="0.00"></td>
                </tr>
              </template>
            </tbody>
          </table>
          <button @click="journalForm.lines.push({account_id:'', debit:'', credit:''})" class="text-sm text-brand-600 mb-4 hover:underline">+ Add Line</button>

          <div class="flex justify-between items-center border-t pt-4">
            <div class="text-sm font-bold">
              Totals: Dr <span x-text="formatCurrency(journalForm.lines.reduce((s,l)=>s+(parseFloat(l.debit)||0),0))"></span> | 
              Cr <span x-text="formatCurrency(journalForm.lines.reduce((s,l)=>s+(parseFloat(l.credit)||0),0))"></span>
            </div>
            <button @click="submitJournal()" class="btn-primary">Post Journal</button>
          </div>
        </div>
      </div>
    </template>

  </div>
</div>

<script>
function reportsPage() {
  return {
    tabs: [
      { id: 'trial', label: 'Trial Balance' },
      { id: 'balance', label: 'Balance Sheet' },
      { id: 'income', label: 'Income Statement' },
    ],
    tab: 'trial', data: null, ledgerData: null,
    accounts: [],
    showJournalModal: false,
    journalForm: {
      date: new Date().toISOString().split('T')[0],
      description: '',
      lines: [{ account_id: '', debit: '', credit: '' }, { account_id: '', debit: '', credit: '' }]
    },

    async load(tabId) {
      if (!requireAuth() || !requireBranch()) return;
      this.tab = tabId; this.data = null;
      const ep = {
        trial: '/accounting/reports/trial-balance/',
        balance: '/accounting/reports/balance-sheet/',
        income: '/accounting/reports/income-statement/',
      }[tabId];
      
      try { 
        this.data = await apiFetch(ep); 
        // Load accounts for the journal modal dropdown
        if (this.accounts.length === 0) {
          this.accounts = await apiFetch('/accounting/accounts/');
        }
      } catch (e) { alert(e.message); }
    },

    async loadLedger(account) {
      try {
        this.ledgerData = await apiFetch(`/accounting/ledger/${account.id}/`);
      } catch(e) { alert("Error loading ledger: " + e.message); }
    },

    async submitJournal() {
      try {
        await apiFetch('/accounting/journals/', { method: 'POST', body: JSON.stringify(this.journalForm) });
        this.showJournalModal = false;
        this.journalForm = { date: new Date().toISOString().split('T')[0], description: '', lines: [{account_id:'', debit:'', credit:''}, {account_id:'', debit:'', credit:''}] };
        this.load('trial');
      } catch(e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
tpl_path.write_text(new_tpl.strip(), encoding="utf-8")
print("✅ Updated templates/pos/reports.html (Added Journal Modals, Drilldown, Fixed UI)")

print("\n🎉 Accounting Module Rebuilt! Run the server and refresh the Reports tab.")