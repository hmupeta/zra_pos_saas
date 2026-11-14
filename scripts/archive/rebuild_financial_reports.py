import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add Cash Flow Backend API
# ============================================================
views_path = BACKEND_PATH / "reports" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

cash_flow_view = '''
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def cash_flow_statement(request):
    """Generates a simple Cash Flow statement based on Cash/Bank account movements."""
    from accounting.models import Account, JournalLine
    from django.db.models import Sum
    from datetime import datetime

    start_date = request.query_params.get("start_date")
    end_date = request.query_params.get("end_date")

    if not start_date or not end_date:
        return Response({"error": "Dates required"}, status=400)

    # Get Cash and Bank accounts
    cash_accounts = Account.objects.filter(tenant=request.tenant, code__in=["1000", "1010"])
    
    # Calculate Inflows (Debits to Cash/Bank)
    inflows = JournalLine.objects.filter(
        account__in=cash_accounts,
        journal__status="POSTED",
        journal__date__range=[start_date, end_date]
    ).aggregate(total=Sum("debit"))["total"] or 0

    # Calculate Outflows (Credits to Cash/Bank)
    outflows = JournalLine.objects.filter(
        account__in=cash_accounts,
        journal__status="POSTED",
        journal__date__range=[start_date, end_date]
    ).aggregate(total=Sum("credit"))["total"] or 0

    net_cash_flow = float(inflows) - float(outflows)

    # Get breakdown of cash movements
    details = JournalLine.objects.filter(
        account__in=cash_accounts,
        journal__status="POSTED",
        journal__date__range=[start_date, end_date]
    ).select_related("journal", "account").order_by("-journal__date")[:50]

    return Response({
        "period": {"start": start_date, "end": end_date},
        "inflows": float(inflows),
        "outflows": float(outflows),
        "net_cash_flow": net_cash_flow,
        "details": [{
            "date": d.journal.date.strftime("%Y-%m-%d"),
            "journal": d.journal.journal_number,
            "description": d.description or d.journal.description,
            "inflow": float(d.debit) if d.debit > 0 else 0,
            "outflow": float(d.credit) if d.credit > 0 else 0
        } for d in details]
    })
'''

if "def cash_flow_statement" not in v_content:
    v_content += "\n\n" + cash_flow_view
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Added Cash Flow backend API.")

# Update URLs
urls_path = BACKEND_PATH / "reports" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "cash_flow_statement" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("cash-flow/", views.cash_flow_statement, name="cash_flow_statement"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
    print("✅ Added Cash Flow URL.")

# ============================================================
# 2. Completely Rebuild reports.html
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "reports.html"
full_html = '''
{% extends "pos/base.html" %}
{% block title %}Financial Reports{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="reportsApp()" x-init="load('trial')">
    
    <!-- Header & Date Range -->
    <div class="flex flex-col md:flex-row justify-between items-start md:items-center mb-6 gap-4">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Financial Reports</h1>
        <p class="text-gray-500 text-sm mt-1">Trial balance, balance sheet, income statement, and cash flow.</p>
      </div>
      
      <div class="flex items-center gap-2 bg-white p-2 rounded-lg border shadow-sm">
        <input type="date" x-model="startDate" class="input-field text-sm py-1.5">
        <span class="text-gray-400">to</span>
        <input type="date" x-model="endDate" class="input-field text-sm py-1.5">
        <button @click="loadCustom()" class="btn-primary text-sm py-1.5 px-4 ml-2">Generate</button>
      </div>
    </div>

    <!-- Tabs Navigation -->
    <div class="flex gap-2 mb-6 border-b border-gray-200 overflow-x-auto pb-1">
      <template x-for="t in tabs" :key="t.id">
        <button @click="load(t.id)" 
                :class="tab === t.id ? 'border-b-2 border-brand-600 text-brand-700 font-bold bg-brand-50' : 'text-gray-500 hover:bg-gray-50 font-medium'"
                class="px-4 py-2 text-sm rounded-t-lg transition-colors whitespace-nowrap">
          <span x-text="t.label"></span>
        </button>
      </template>
    </div>

    <!-- Loading State -->
    <div x-show="loading" class="flex justify-center py-20">
      <div class="animate-spin rounded-full h-10 w-10 border-b-2 border-brand-600"></div>
    </div>

    <!-- Content Area -->
    <div x-show="!loading && data" class="animate-fade-in">
      
      <!-- 1. Trial Balance -->
      <div x-show="tab === 'trial'" class="card overflow-hidden">
        <div class="p-4 border-b bg-gray-50 flex justify-between items-center">
          <h2 class="font-bold text-slate-800">Trial Balance</h2>
          <button @click="exportCsv('Trial_Balance', data?.accounts)" class="btn-secondary text-xs">Export CSV</button>
        </div>
        <table class="w-full text-sm">
          <thead class="bg-white text-left text-xs uppercase text-gray-500 border-b">
            <tr>
              <th class="px-6 py-3">Code</th>
              <th class="px-6 py-3">Account Name</th>
              <th class="px-6 py-3 text-right">Debit (K)</th>
              <th class="px-6 py-3 text-right">Credit (K)</th>
            </tr>
          </thead>
          <tbody>
            <template x-for="a in data.accounts || []" :key="a.code">
              <tr class="border-b hover:bg-gray-50">
                <td class="px-6 py-3 font-mono text-xs text-brand-600" x-text="a.code"></td>
                <td class="px-6 py-3 font-medium text-slate-700" x-text="a.name"></td>
                <td class="px-6 py-3 text-right" x-text="a.debit > 0 ? formatCurrency(a.debit) : '-'"></td>
                <td class="px-6 py-3 text-right" x-text="a.credit > 0 ? formatCurrency(a.credit) : '-'"></td>
              </tr>
            </template>
            <tr class="bg-gray-100 font-bold border-t-2">
              <td class="px-6 py-4" colSpan="2">TOTALS</td>
              <td class="px-6 py-4 text-right" x-text="formatCurrency(data.total_debit)"></td>
              <td class="px-6 py-4 text-right" x-text="formatCurrency(data.total_credit)"></td>
            </tr>
          </tbody>
        </table>
        <div x-show="data && !data.balanced" class="p-3 bg-red-100 text-red-800 text-center font-bold text-sm">
          ⚠️ Books are NOT balanced. Debits must equal Credits.
        </div>
      </div>

      <!-- 2. Balance Sheet -->
      <div x-show="tab === 'balance'" class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div class="card p-6 border-t-4 border-green-500">
          <h2 class="text-xl font-bold mb-6 text-slate-800">Assets</h2>
          <div class="flex justify-between items-center border-b pb-4 mb-4">
            <span class="text-gray-500 font-medium">Total Assets</span>
            <span class="text-2xl font-bold text-green-700" x-text="formatCurrency(data?.assets)"></span>
          </div>
        </div>
        <div class="card p-6 border-t-4 border-brand-500">
          <h2 class="text-xl font-bold mb-6 text-slate-800">Liabilities & Equity</h2>
          <div class="space-y-3 text-sm">
            <div class="flex justify-between"><span class="text-gray-500">Liabilities</span><span class="font-medium" x-text="formatCurrency(data?.liabilities)"></span></div>
            <div class="flex justify-between"><span class="text-gray-500">Equity</span><span class="font-medium" x-text="formatCurrency(data?.equity)"></span></div>
            <div class="flex justify-between"><span class="text-gray-500">Net Income</span><span class="font-medium" x-text="formatCurrency(data?.net_income)"></span></div>
            <div class="flex justify-between border-t pt-3 mt-3 font-bold text-lg">
              <span>Total L&E</span>
              <span class="text-brand-700" x-text="formatCurrency((data?.liabilities||0) + (data?.equity||0) + (data?.net_income||0))"></span>
            </div>
          </div>
        </div>
      </div>

      <!-- 3. Income Statement -->
      <div x-show="tab === 'income'" class="card p-6 max-w-3xl border-t-4 border-purple-500">
        <h2 class="text-xl font-bold mb-6 text-slate-800">Income Statement (P&L)</h2>
        <div class="flex justify-between py-3 border-b"><span class="text-gray-600 font-medium">Total Revenue</span><span class="font-bold" x-text="formatCurrency(data?.revenue)"></span></div>
        <div class="flex justify-between py-3 border-b"><span class="text-gray-600 font-medium">Total Expenses</span><span class="font-bold text-red-600" x-text="formatCurrency(data?.expenses)"></span></div>
        <div class="flex justify-between py-4 text-2xl font-bold">
          <span>Net Income</span>
          <span :class="data?.net_income >= 0 ? 'text-green-600' : 'text-red-600'" x-text="formatCurrency(data?.net_income)"></span>
        </div>
        <div class="text-sm text-gray-500 bg-gray-50 p-3 rounded">Profit Margin: <span class="font-bold" x-text="(data?.margin_percent || 0).toFixed(1)"></span>%</div>
      </div>

      <!-- 4. Cash Flow -->
      <div x-show="tab === 'cash_flow'" class="space-y-6">
        <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="card p-6 border-l-4 border-green-500">
            <div class="text-sm text-gray-500 font-medium">Cash Inflows</div>
            <div class="text-2xl font-bold text-green-700 mt-1" x-text="formatCurrency(data?.inflows)"></div>
          </div>
          <div class="card p-6 border-l-4 border-red-500">
            <div class="text-sm text-gray-500 font-medium">Cash Outflows</div>
            <div class="text-2xl font-bold text-red-700 mt-1" x-text="formatCurrency(data?.outflows)"></div>
          </div>
          <div class="card p-6 bg-slate-900 text-white">
            <div class="text-sm text-slate-300 font-medium">Net Cash Flow</div>
            <div class="text-2xl font-bold mt-1" :class="data?.net_cash_flow >= 0 ? 'text-green-400' : 'text-red-400'" x-text="formatCurrency(data?.net_cash_flow)"></div>
          </div>
        </div>

        <div class="card overflow-hidden">
          <div class="p-4 border-b bg-gray-50"><h3 class="font-bold text-slate-800">Cash Movement Details</h3></div>
          <table class="w-full text-sm">
            <thead class="bg-white text-left text-xs uppercase text-gray-500 border-b">
              <tr><th class="px-6 py-3">Date</th><th class="px-6 py-3">Ref</th><th class="px-6 py-3">Description</th><th class="px-6 py-3 text-right text-green-600">Inflow</th><th class="px-6 py-3 text-right text-red-600">Outflow</th></tr>
            </thead>
            <tbody>
              <template x-for="d in data.details || []" :key="d.journal + d.date">
                <tr class="border-b hover:bg-gray-50">
                  <td class="px-6 py-3 text-gray-500" x-text="d.date"></td>
                  <td class="px-6 py-3 font-mono text-xs text-brand-600" x-text="d.journal"></td>
                  <td class="px-6 py-3" x-text="d.description"></td>
                  <td class="px-6 py-3 text-right font-medium text-green-700" x-text="d.inflow > 0 ? formatCurrency(d.inflow) : '-'"></td>
                  <td class="px-6 py-3 text-right font-medium text-red-700" x-text="d.outflow > 0 ? formatCurrency(d.outflow) : '-'"></td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 5. Sales by Category -->
      <div x-show="tab === 'category'" class="card overflow-hidden">
        <div class="p-4 border-b bg-gray-50 flex justify-between items-center">
          <h2 class="font-bold text-slate-800">Revenue by Category</h2>
          <button @click="exportCsv('Sales_By_Category', data)" class="btn-secondary text-xs">Export CSV</button>
        </div>
        <table class="w-full text-sm">
          <thead class="bg-white text-left text-xs uppercase text-gray-500 border-b">
            <tr><th class="px-6 py-3">Category</th><th class="px-6 py-3 text-right">Qty Sold</th><th class="px-6 py-3 text-right">Total Revenue</th></tr>
          </thead>
          <tbody>
            <template x-for="c in data || []" :key="c.category">
              <tr class="border-b hover:bg-gray-50">
                <td class="px-6 py-3 font-medium text-slate-700" x-text="c.category"></td>
                <td class="px-6 py-3 text-right" x-text="c.qty"></td>
                <td class="px-6 py-3 text-right font-bold text-brand-700" x-text="formatCurrency(c.revenue)"></td>
              </tr>
            </template>
          </tbody>
        </table>
        <div x-show="data && data.length === 0" class="p-8 text-center text-gray-400">No sales in this period.</div>
      </div>

    </div>
  </div>
</div>

<script>
function reportsApp() {
  return {
    tabs: [
      { id: 'trial', label: 'Trial Balance' },
      { id: 'balance', label: 'Balance Sheet' },
      { id: 'income', label: 'Income Statement' },
      { id: 'cash_flow', label: 'Cash Flow' },
      { id: 'category', label: 'Sales by Category' },
    ],
    tab: 'trial', data: null, loading: false,
    startDate: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().split('T')[0],
    endDate: new Date().toISOString().split('T')[0],

    async load(tabId) {
      if (!requireAuth()) return;
      this.tab = tabId;
      this.fetchData();
    },

    async loadCustom() {
      this.fetchData();
    },

    async fetchData() {
      this.loading = true;
      this.data = null;
      
      let endpoint = '';
      const params = `?start_date=${this.startDate}&end_date=${this.endDate}`;

      if (this.tab === 'trial') endpoint = '/accounting/reports/trial-balance/';
      if (this.tab === 'balance') endpoint = '/accounting/reports/balance-sheet/';
      if (this.tab === 'income') endpoint = '/accounting/reports/income-statement/';
      if (this.tab === 'cash_flow') endpoint = '/reports/cash-flow/';
      if (this.tab === 'category') endpoint = '/reports/sales-by-category/';

      try {
        // Append params to accounting endpoints if they support it
        const url = (this.tab === 'cash_flow' || this.tab === 'category') ? endpoint + params : endpoint;
        this.data = await apiFetch(url);
      } catch (e) {
        alert('Error loading report: ' + e.message);
      } finally {
        this.loading = false;
      }
    },

    exportCsv(filename, rows) {
      if (!rows || rows.length === 0) { alert('No data to export'); return; }
      const headers = Object.keys(rows[0]);
      const csvContent = [
        headers.join(','),
        ...rows.map(r => headers.map(h => `"${r[h]}"`).join(','))
      ].join('\\n');
      
      const blob = new Blob([csvContent], { type: 'text/csv' });
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${filename}_${this.startDate}_to_${this.endDate}.csv`;
      a.click();
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(full_html.strip(), encoding="utf-8")
print("✅ Completely rebuilt reports.html with clean UI and Cash Flow tab.")

print("\n🎉 Done! Restart the server and go to Financial Reports.")