import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def patch_file(path, old, new, is_regex=False):
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if is_regex:
        content = re.sub(old, new, content, flags=re.DOTALL)
    else:
        content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")

# ============================================================
# 1. Update accounting/views.py (Add POST to accounts_list)
# ============================================================
acc_views = BACKEND_PATH / "accounting" / "views.py"
content = acc_views.read_text(encoding="utf-8")

new_accounts_list = '''
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def accounts_list(request):
    if request.method == "GET":
        qs = Account.objects.filter(tenant=request.tenant, is_active=True)
        return Response([{
            "id": a.id, "code": a.code, "name": a.name, "type": a.account_type,
            "balance": float(a.balance()), "is_header": a.is_header
        } for a in qs])
    
    # POST: Create account
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Only Admins or Managers can create accounts"}, status=403)
        
    data = request.data
    if not data.get("code") or not data.get("name") or not data.get("account_type"):
        return Response({"error": "Code, Name and Type are required"}, status=400)
        
    account, created = Account.objects.get_or_create(
        tenant=request.tenant, code=data["code"],
        defaults={
            "name": data["name"],
            "account_type": data["account_type"],
            "is_header": data.get("is_header", False),
            "opening_balance": data.get("opening_balance", 0),
        }
    )
    return Response({"success": True, "id": account.id}, status=201)
'''

# Replace the old accounts_list
content = re.sub(r"@api_view\(\[\"GET\"\]\).*?return Response\(\[\{\n        \"id\": a.id.*?\}\]\)", new_accounts_list.strip(), content, flags=re.DOTALL)
acc_views.write_text(content, encoding="utf-8")
print("✅ Updated accounting/views.py to support creating accounts")

# ============================================================
# 2. Add views to core/views_web.py
# ============================================================
web_views = BACKEND_PATH / "core" / "views_web.py"
wv_content = web_views.read_text(encoding="utf-8")
if "def coa_page" not in wv_content:
    wv_content += """

def coa_page(request):
    return render(request, "pos/accounting_coa.html")

def journals_page(request):
    return render(request, "pos/accounting_journals.html")

def ledger_page(request):
    return render(request, "pos/accounting_ledger.html")
"""
    web_views.write_text(wv_content, encoding="utf-8")
print("✅ Added UI views for Accounting pages")

# ============================================================
# 3. Add URLs to core/urls_web.py
# ============================================================
web_urls = BACKEND_PATH / "core" / "urls_web.py"
wu_content = web_urls.read_text(encoding="utf-8")
if "/accounting/coa" not in wu_content:
    wu_content = wu_content.replace(
        "urlpatterns = [",
        '''urlpatterns = [
    path("accounting/coa", views_web.coa_page, name="coa_page"),
    path("accounting/journals", views_web.journals_page, name="journals_page"),
    path("accounting/ledger", views_web.ledger_page, name="ledger_page"),'''
    )
    web_urls.write_text(wu_content, encoding="utf-8")
print("✅ Added URLs for Accounting pages")

# ============================================================
# 4. Update Navigation (_nav.html)
# ============================================================
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")

old_nav_link = '''<a href="/reports" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">Financial Reports</a>'''
new_nav_links = '''<a href="/reports" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">Financial Reports</a>
    <a href="/accounting/coa" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">Chart of Accounts</a>
    <a href="/accounting/journals" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">Journal Entries</a>
    <a href="/accounting/ledger" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">General Ledger</a>'''

nav_content = nav_content.replace(old_nav_link, new_nav_links)
nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Updated Sidebar Navigation with Accounting links")

# ============================================================
# 5. Create Accounting UI Templates
# ============================================================
coa_html = '''
{% extends "pos/base.html" %}
{% block title %}Chart of Accounts{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="coaPage()" x-init="load()">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Chart of Accounts</h1>
      <button @click="showModal = true" class="btn-primary">+ New Account</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Code</th>
            <th class="px-4 py-3">Account Name</th>
            <th class="px-4 py-3">Type</th>
            <th class="px-4 py-3 text-right">Balance</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="a in accounts" :key="a.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-mono" x-text="a.code"></td>
              <td class="px-4 py-3 font-medium" x-text="a.name"></td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded text-xs bg-gray-100 text-gray-700" x-text="a.type"></span>
              </td>
              <td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(a.balance)"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4">New Account</h2>
          <form @submit.prevent="create()" class="space-y-3">
            <input placeholder="Account Code (e.g. 1000)" x-model="form.code" class="input-field" required>
            <input placeholder="Account Name (e.g. Cash on Hand)" x-model="form.name" class="input-field" required>
            <select x-model="form.account_type" class="input-field">
              <option value="ASSET">Asset</option>
              <option value="LIABILITY">Liability</option>
              <option value="EQUITY">Equity</option>
              <option value="REVENUE">Revenue</option>
              <option value="EXPENSE">Expense</option>
            </select>
            <input type="number" step="0.01" placeholder="Opening Balance (Optional)" x-model="form.opening_balance" class="input-field">
            <button type="submit" class="btn-primary w-full">Create Account</button>
          </form>
        </div>
      </div>
    </template>
  </div>
</div>
<script>
function coaPage() {
  return {
    accounts: [], showModal: false,
    form: { code: '', name: '', account_type: 'ASSET', opening_balance: 0 },
    async load() {
      if (!requireAuth()) return;
      try { this.accounts = await apiFetch('/accounting/accounts/'); } catch(e) { alert(e.message); }
    },
    async create() {
      try {
        await apiFetch('/accounting/accounts/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        this.form = { code: '', name: '', account_type: 'ASSET', opening_balance: 0 };
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''

journals_html = '''
{% extends "pos/base.html" %}
{% block title %}Journal Entries{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="journalsPage()" x-init="load()">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Journal Entries</h1>
      <button @click="showModal = true" class="btn-primary">+ Manual Entry</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Date</th>
            <th class="px-4 py-3">Ref</th>
            <th class="px-4 py-3">Description</th>
            <th class="px-4 py-3">Type</th>
            <th class="px-4 py-3 text-right">Amount</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="j in journals" :key="j.id">
            <tr class="border-t hover:bg-gray-50 cursor-pointer" @click="viewJournal(j)">
              <td class="px-4 py-3" x-text="j.date"></td>
              <td class="px-4 py-3 font-mono text-xs" x-text="j.journal_number"></td>
              <td class="px-4 py-3 font-medium" x-text="j.description"></td>
              <td class="px-4 py-3"><span class="text-xs px-2 py-0.5 bg-blue-100 text-blue-800 rounded" x-text="j.journal_type"></span></td>
              <td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(j.total)"></td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- New Journal Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-2xl w-full p-6">
          <h2 class="text-xl font-bold mb-4">New Journal Entry</h2>
          <div class="grid grid-cols-2 gap-4 mb-4">
            <div>
              <label class="block text-sm mb-1">Date</label>
              <input type="date" x-model="form.date" class="input-field">
            </div>
            <div>
              <label class="block text-sm mb-1">Description</label>
              <input type="text" x-model="form.description" placeholder="e.g. Paid Rent" class="input-field">
            </div>
          </div>
          
          <table class="w-full text-sm mb-4">
            <thead><tr><th class="text-left pb-2">Account</th><th class="text-right pb-2">Debit</th><th class="text-right pb-2">Credit</th></tr></thead>
            <tbody>
              <template x-for="(line, idx) in form.lines" :key="idx">
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
          <button @click="form.lines.push({account_id:'', debit:'', credit:''})" class="text-sm text-brand-600 mb-4 hover:underline">+ Add Line</button>

          <div class="flex justify-between items-center border-t pt-4">
            <div class="text-sm font-bold">
              Totals: Dr <span x-text="formatCurrency(form.lines.reduce((s,l)=>s+(parseFloat(l.debit)||0),0))"></span> | 
              Cr <span x-text="formatCurrency(form.lines.reduce((s,l)=>s+(parseFloat(l.credit)||0),0))"></span>
            </div>
            <button @click="submitJournal()" class="btn-primary">Post Journal</button>
          </div>
        </div>
      </div>
    </template>
  </div>
</div>
<script>
function journalsPage() {
  return {
    journals: [], accounts: [], showModal: false,
    form: {
      date: new Date().toISOString().split('T')[0],
      description: '',
      lines: [{ account_id: '', debit: '', credit: '' }, { account_id: '', debit: '', credit: '' }]
    },
    async load() {
      if (!requireAuth()) return;
      try {
        this.journals = await apiFetch('/accounting/journals/');
        this.accounts = await apiFetch('/accounting/accounts/');
      } catch(e) { alert(e.message); }
    },
    async submitJournal() {
      try {
        await apiFetch('/accounting/journals/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        this.form = { date: new Date().toISOString().split('T')[0], description: '', lines: [{account_id:'', debit:'', credit:''}, {account_id:'', debit:'', credit:''}] };
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },
    viewJournal(j) {
      alert("Journal Details:\n" + j.description + "\nTotal: " + formatCurrency(j.total));
    }
  }
}
</script>
{% endblock %}
'''

ledger_html = '''
{% extends "pos/base.html" %}
{% block title %}General Ledger{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="ledgerPage()" x-init="loadAccounts()">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">General Ledger</h1>
    </div>

    <div class="card p-4 mb-6">
      <label class="block text-sm font-medium mb-2">Select Account to view transactions</label>
      <select x-model="selectedAccountId" @change="loadLedger()" class="input-field max-w-md">
        <option value="">-- Choose an account --</option>
        <template x-for="a in accounts" :key="a.id">
          <option :value="a.id" x-text="a.code + ' - ' + a.name"></option>
        </template>
      </select>
    </div>

    <div x-show="ledgerData" class="card overflow-hidden">
      <div class="bg-gray-50 p-4 border-b flex justify-between">
        <div>
          <h3 class="font-bold text-lg" x-text="ledgerData?.account?.name"></h3>
          <p class="text-sm text-gray-500">Code: <span x-text="ledgerData?.account?.code"></span> | Type: <span x-text="ledgerData?.account?.type"></span></p>
        </div>
      </div>
      <table class="w-full text-sm">
        <thead class="bg-gray-100 text-left text-xs uppercase text-gray-600">
          <tr>
            <th class="px-4 py-3">Date</th>
            <th class="px-4 py-3">Ref</th>
            <th class="px-4 py-3">Description</th>
            <th class="px-4 py-3 text-right">Debit</th>
            <th class="px-4 py-3 text-right">Credit</th>
            <th class="px-4 py-3 text-right">Balance</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="e in ledgerData?.entries || []" :key="e.reference">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3" x-text="e.date"></td>
              <td class="px-4 py-3 font-mono text-xs" x-text="e.reference"></td>
              <td class="px-4 py-3" x-text="e.description"></td>
              <td class="px-4 py-3 text-right" x-text="e.debit > 0 ? formatCurrency(e.debit) : '-'"></td>
              <td class="px-4 py-3 text-right" x-text="e.credit > 0 ? formatCurrency(e.credit) : '-'"></td>
              <td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(e.balance)"></td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="ledgerData?.entries?.length === 0" class="p-8 text-center text-gray-500">
        No transactions found for this account.
      </div>
    </div>
  </div>
</div>
<script>
function ledgerPage() {
  return {
    accounts: [], selectedAccountId: '', ledgerData: null,
    async loadAccounts() {
      if (!requireAuth()) return;
      try { this.accounts = await apiFetch('/accounting/accounts/'); } catch(e) { alert(e.message); }
    },
    async loadLedger() {
      if (!this.selectedAccountId) { this.ledgerData = null; return; }
      try {
        this.ledgerData = await apiFetch(`/accounting/ledger/${this.selectedAccountId}/`);
      } catch(e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''

(Path(BACKEND_PATH) / "templates" / "pos" / "accounting_coa.html").write_text(coa_html.strip(), encoding="utf-8")
(Path(BACKEND_PATH) / "templates" / "pos" / "accounting_journals.html").write_text(journals_html.strip(), encoding="utf-8")
(Path(BACKEND_PATH) / "templates" / "pos" / "accounting_ledger.html").write_text(ledger_html.strip(), encoding="utf-8")
print("✅ Created 3 new Accounting UI templates")
print("🎉 Accounting UI Complete! Restart server to view.")