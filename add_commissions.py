import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add SalesTarget Model
# ============================================================
models_path = BACKEND_PATH / "sales" / "models.py"
content = models_path.read_text(encoding="utf-8")

if "class SalesTarget" not in content:
    content += '''

class SalesTarget(models.Model):
    tenant = models.ForeignKey("core.Tenant", on_delete=models.CASCADE)
    agent = models.ForeignKey("core.User", on_delete=models.CASCADE, related_name="sales_targets")
    month = models.IntegerField() # 1-12
    year = models.IntegerField()
    target_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    commission_rate = models.DecimalField(max_digits=5, decimal_places=2, default=2.0, help_text="Percentage, e.g. 2.5")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("tenant", "agent", "month", "year")]

    def __str__(self):
        return f"{self.agent.username} - {self.month}/{self.year}"
'''
    models_path.write_text(content, encoding="utf-8")
print("✅ Added SalesTarget model")

# ============================================================
# 2. Add API View for Targets & Performance
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

target_views = '''
from django.db.models import Sum
from django.utils import timezone
from datetime import datetime

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def agent_targets(request):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)
        
    now = timezone.now()
    
    if request.method == "GET":
        month = int(request.query_params.get("month", now.month))
        year = int(request.query_params.get("year", now.year))
        
        # Get all sales agents in this tenant
        agents = request.tenant.users.filter(user_type="SALES_AGENT", is_active=True)
        
        data = []
        for agent in agents:
            # 1. Get target
            target = SalesTarget.objects.filter(tenant=request.tenant, agent=agent, month=month, year=year).first()
            target_amt = float(target.target_amount) if target else 0
            comm_rate = float(target.commission_rate) if target else 2.0
            
            # 2. Calculate actual sales for this month
            invoices = Invoice.objects.filter(
                tenant=request.tenant, cashier=agent, status="PAID",
                created_at__year=year, created_at__month=month
            )
            actual_sales = float(invoices.aggregate(t=Sum("total"))["t"] or 0)
            
            # 3. Calculate commission
            commission_earned = actual_sales * (comm_rate / 100)
            
            # 4. Calculate progress %
            progress = (actual_sales / target_amt * 100) if target_amt > 0 else 0

            data.append({
                "agent_id": agent.id,
                "agent_name": agent.username,
                "month": month,
                "year": year,
                "target_amount": target_amt,
                "actual_sales": actual_sales,
                "commission_rate": comm_rate,
                "commission_earned": commission_earned,
                "progress": min(round(progress, 1), 100) # Cap at 100 for UI progress bar
            })
            
        return Response(data)
        
    elif request.method == "POST":
        # Set/Update Target
        data = request.data
        agent_id = data.get("agent_id")
        month = data.get("month")
        year = data.get("year")
        target_amount = data.get("target_amount")
        commission_rate = data.get("commission_rate")
        
        target, created = SalesTarget.objects.update_or_create(
            tenant=request.tenant, agent_id=agent_id, month=month, year=year,
            defaults={"target_amount": target_amount, "commission_rate": commission_rate}
        )
        return Response({"success": True})
'''

if "def agent_targets" not in v_content:
    views_path.write_text(v_content + "\n\n" + target_views, encoding="utf-8")

# Update URLs
urls_path = BACKEND_PATH / "sales" / "urls.py"
u_content = urls_path.read_text(encoding="utf-8")
if "agent_targets" not in u_content:
    u_content = u_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("agent-targets/", views.agent_targets, name="agent_targets"),'
    )
    urls_path.write_text(u_content, encoding="utf-8")
print("✅ Added Agent Targets API")

# ============================================================
# 3. Frontend: Route & Nav
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
w_content = views_web.read_text(encoding="utf-8")
if "def commissions_page" not in w_content:
    w_content += "\n\ndef commissions_page(request):\n    return render(request, 'pos/commissions.html')\n"
    views_web.write_text(w_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
wu_content = urls_web.read_text(encoding="utf-8")
if "/commissions" not in wu_content:
    wu_content = wu_content.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('commissions', views_web.commissions_page, name='commissions_page'),"
    )
    urls_web.write_text(wu_content, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
n_content = nav_path.read_text(encoding="utf-8")
if "href=\"/commissions\"" not in n_content:
    n_content = n_content.replace(
        '<a href="/audit" class="nav-link"',
        '<a href="/commissions" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)"><i data-lucide="target" class="w-4 h-4 mr-3"></i> Commissions</a>\n    <a href="/audit" class="nav-link"'
    )
    nav_path.write_text(n_content, encoding="utf-8")
print("✅ Added Commissions to Sidebar")

# ============================================================
# 4. Frontend: Commissions UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "commissions.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Commissions{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="commissionsApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Sales Targets & Commissions</h1>
        <p class="text-gray-500 text-sm mt-1">Track agent performance and calculate payroll.</p>
      </div>
      
      <div class="flex gap-2">
        <select x-model="month" @change="load()" class="input-field w-32 bg-white">
          <template x-for="(m, index) in months" :key="index">
            <option :value="index + 1" x-text="m"></option>
          </template>
        </select>
        <select x-model="year" @change="load()" class="input-field w-32 bg-white">
          <template x-for="y in [2024, 2025, 2026, 2027]" :key="y">
            <option :value="y" x-text="y"></option>
          </template>
        </select>
      </div>
    </div>

    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
      <template x-for="agent in data" :key="agent.agent_id">
        <div class="card p-6 border-t-4 border-brand-500">
          <div class="flex justify-between items-start mb-4">
            <div class="flex items-center gap-3">
              <div class="w-10 h-10 bg-brand-100 text-brand-700 rounded-full flex items-center justify-center font-bold text-lg">
                <span x-text="agent.agent_name.charAt(0).toUpperCase()"></span>
              </div>
              <div>
                <div class="font-bold text-slate-800" x-text="agent.agent_name"></div>
                <div class="text-xs text-gray-500">Sales Agent</div>
              </div>
            </div>
            <button @click="openEditModal(agent)" class="text-gray-400 hover:text-brand-600">
              <i data-lucide="settings" class="w-4 h-4"></i>
            </button>
          </div>

          <!-- Progress Bar -->
          <div class="mb-2 flex justify-between text-sm">
            <span class="text-gray-500">Target Progress</span>
            <span class="font-bold" x-text="agent.progress + '%'"></span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-2.5 mb-6">
            <div class="bg-brand-600 h-2.5 rounded-full transition-all duration-500" :style="`width: ${agent.progress}%`"></div>
          </div>

          <!-- Financials -->
          <div class="space-y-3 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-500">Actual Sales:</span>
              <span class="font-bold text-slate-800" x-text="formatCurrency(agent.actual_sales)"></span>
            </div>
            <div class="flex justify-between border-b pb-3">
              <span class="text-gray-500">Target Amount:</span>
              <span class="font-bold text-slate-800" x-text="formatCurrency(agent.target_amount)"></span>
            </div>
            <div class="flex justify-between pt-1">
              <span class="text-gray-500">Commission Rate:</span>
              <span class="font-bold" x-text="agent.commission_rate + '%'"></span>
            </div>
            <div class="flex justify-between bg-green-50 p-2 rounded border border-green-100">
              <span class="text-green-800 font-medium">Commission Payout:</span>
              <span class="font-bold text-green-700" x-text="formatCurrency(agent.commission_earned)"></span>
            </div>
          </div>
        </div>
      </template>
    </div>

    <!-- Edit Target Modal -->
    <template x-if="editModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-sm w-full p-6">
          <h2 class="text-xl font-bold mb-4" x-text="'Set Target for ' + form.agent_name"></h2>
          <form @submit.prevent="saveTarget()" class="space-y-4">
            <div>
              <label class="block text-sm mb-1">Monthly Target (K)</label>
              <input type="number" step="100" x-model="form.target_amount" class="input-field font-bold" required>
            </div>
            <div>
              <label class="block text-sm mb-1">Commission Rate (%)</label>
              <input type="number" step="0.1" x-model="form.commission_rate" class="input-field font-bold" required>
              <p class="text-xs text-gray-500 mt-1">e.g. 2.5 for 2.5% of total sales</p>
            </div>
            <div class="flex gap-2 pt-2">
              <button type="button" @click="editModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1">Save Target</button>
            </div>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function commissionsApp() {
  return {
    data: [], month: new Date().getMonth() + 1, year: new Date().getFullYear(),
    months: ['January','February','March','April','May','June','July','August','September','October','November','December'],
    editModal: false,
    form: { agent_id: null, agent_name: '', target_amount: 0, commission_rate: 2.0 },

    async load() {
      if (!requireAuth()) return;
      try {
        this.data = await apiFetch(`/sales/agent-targets/?month=${this.month}&year=${this.year}`);
        setTimeout(() => { lucide.createIcons(); }, 50);
      } catch(e) { alert(e.message); }
    },

    openEditModal(agent) {
      this.form = { 
        agent_id: agent.agent_id, 
        agent_name: agent.agent_name, 
        target_amount: agent.target_amount || 0,
        commission_rate: agent.commission_rate || 2.0
      };
      this.editModal = true;
    },

    async saveTarget() {
      try {
        await apiFetch('/sales/agent-targets/', {
          method: 'POST',
          body: JSON.stringify({
            agent_id: this.form.agent_id,
            month: this.month,
            year: this.year,
            target_amount: this.form.target_amount,
            commission_rate: this.form.commission_rate
          })
        });
        this.editModal = false;
        this.load();
      } catch(e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created commissions.html UI")

# ============================================================
# 5. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "sales"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! Restart the server.")