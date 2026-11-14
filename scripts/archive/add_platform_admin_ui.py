import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add Views & URLs for Platform Admin
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")

if "def platform_dashboard_page" not in web_content:
    web_content += """

def platform_dashboard_page(request):
    return render(request, "pos/platform_dashboard.html")

def platform_tenants_page(request):
    return render(request, "pos/platform_tenants.html")

def platform_applications_page(request):
    return render(request, "pos/platform_applications.html")
"""
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/platform" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('platform', views_web.platform_dashboard_page, name='platform_dashboard'),\n"
        "    path('platform/tenants', views_web.platform_tenants_page, name='platform_tenants'),\n"
        "    path('platform/applications', views_web.platform_applications_page, name='platform_applications'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")
print("✅ Added Platform Admin routes")

# ============================================================
# 2. Update Base Template for Platform Admin
# ============================================================
# We'll reuse base.html but need a different nav. Let's create a dedicated platform base.
base_path = BACKEND_PATH / "templates" / "pos" / "base.html"
base_content = base_path.read_text(encoding="utf-8")

# Add a check to load a different nav if we are on the platform route
base_content = base_content.replace(
    "<body class=\"text-slate-800 antialiased\">\n  {% block body %}{% endblock %}",
    "<body class=\"text-slate-800 antialiased\">\n  {% block body %}{% endblock %}"
)
base_path.write_text(base_content, encoding="utf-8")

# ============================================================
# 3. Create the Platform Dashboard UI
# ============================================================
dash_path = BACKEND_PATH / "templates" / "pos" / "platform_dashboard.html"
dash_html = '''
{% extends "pos/base.html" %}
{% block title %}Platform Admin{% endblock %}
{% block body %}
<div class="h-screen flex bg-slate-50">
  
  <!-- Sidebar -->
  <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col shadow-2xl z-20">
    <div class="h-16 flex items-center px-6 border-b border-slate-800 bg-slate-950/50">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center text-white shadow-lg">
          <i data-lucide="shield" class="w-5 h-5"></i>
        </div>
        <div>
          <div class="font-bold text-white tracking-wide text-lg">Nimbus HQ</div>
          <div class="text-[10px] text-slate-400 uppercase tracking-wider">Platform Admin</div>
        </div>
      </div>
    </div>
    <nav class="flex-1 py-6 px-4 space-y-1">
      <a href="/platform" class="nav-link active"><i data-lucide="layout-dashboard" class="w-4 h-4 mr-3"></i> Overview</a>
      <a href="/platform/tenants" class="nav-link"><i data-lucide="building" class="w-4 h-4 mr-3"></i> Tenants</a>
      <a href="/platform/applications" class="nav-link"><i data-lucide="file-text" class="w-4 h-4 mr-3"></i> Applications</a>
      <div class="pt-4 mt-4 border-t border-slate-800">
        <a href="/pos" class="nav-link text-indigo-400"><i data-lucide="external-link" class="w-4 h-4 mr-3"></i> View Tenant POS</a>
      </div>
    </nav>
    <div class="p-4 border-t border-slate-800 bg-slate-950/50">
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-3">
          <div class="w-9 h-9 rounded-full bg-slate-800 flex items-center justify-center font-bold text-white">A</div>
          <div>
            <div class="text-sm font-medium text-white">Super Admin</div>
            <div class="text-[10px] text-indigo-400 font-semibold uppercase">HQ Access</div>
          </div>
        </div>
        <button onclick="logout()" class="text-slate-400 hover:text-red-400"><i data-lucide="log-out" class="w-5 h-5"></i></button>
      </div>
    </div>
  </aside>

  <!-- Main Content -->
  <div class="flex-1 overflow-y-auto p-8" x-data="platformDash()" x-init="load()">
    <div class="flex justify-between items-end mb-8">
      <div>
        <h1 class="text-3xl font-bold text-slate-900 tracking-tight">SaaS Overview</h1>
        <p class="text-slate-500 mt-1">Platform performance and tenant metrics</p>
      </div>
    </div>

    <!-- KPI Cards -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8" x-show="data">
      <div class="card p-6 border-l-4 border-l-green-500">
        <div class="text-sm font-medium text-gray-500 mb-1">Monthly Recurring Revenue</div>
        <div class="text-3xl font-bold text-slate-900" x-text="formatCurrency(data?.kpis.mrr)"></div>
        <div class="text-sm text-green-600 mt-2 font-medium">ARR: <span x-text="formatCurrency(data?.kpis.arr)"></span></div>
      </div>
      <div class="card p-6 border-l-4 border-l-indigo-500">
        <div class="text-sm font-medium text-gray-500 mb-1">Active Tenants</div>
        <div class="text-3xl font-bold text-slate-900" x-text="data?.kpis.active_tenants"></div>
        <div class="text-sm text-gray-500 mt-2"><span x-text="data?.kpis.trial_tenants"></span> on free trial</div>
      </div>
      <div class="card p-6 border-l-4 border-l-orange-500">
        <div class="text-sm font-medium text-gray-500 mb-1">Pending Signups</div>
        <div class="text-3xl font-bold text-slate-900" x-text="data?.kpis.pending_applications"></div>
        <a href="/platform/applications" class="text-sm text-orange-600 hover:underline mt-2 inline-block font-medium">Review now &rarr;</a>
      </div>
      <div class="card p-6 border-l-4 border-l-red-500">
        <div class="text-sm font-medium text-gray-500 mb-1">Outstanding Billing</div>
        <div class="text-3xl font-bold text-slate-900" x-text="formatCurrency(data?.kpis.outstanding_balance)"></div>
        <div class="text-sm text-red-600 mt-2 font-medium">Needs collection</div>
      </div>
    </div>

    <!-- Recent Activity -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6" x-show="data">
      
      <!-- Recent Signups -->
      <div class="card p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="font-bold text-lg text-slate-900">Recent Applications</h2>
          <a href="/platform/applications" class="text-sm text-indigo-600 hover:underline">View All</a>
        </div>
        <div class="space-y-3">
          <template x-for="s in data?.recent_signups" :key="s.id">
            <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-100">
              <div>
                <div class="font-bold text-sm text-slate-900" x-text="s.business_name"></div>
                <div class="text-xs text-gray-500" x-text="s.contact_email"></div>
              </div>
              <span class="px-2 py-1 rounded text-xs font-bold uppercase"
                    :class="s.status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' : 'bg-green-100 text-green-700'"
                    x-text="s.status"></span>
            </div>
          </template>
        </div>
      </div>

      <!-- Recent Payments -->
      <div class="card p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="font-bold text-lg text-slate-900">Recent Revenue</h2>
        </div>
        <div class="space-y-3">
          <template x-for="p in data?.recent_payments" :key="p.id">
            <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg border border-gray-100">
              <div>
                <div class="font-bold text-sm text-slate-900" x-text="p.tenant_name"></div>
                <div class="text-xs text-gray-500" x-text="p.payment_method + ' · ' + p.payment_date"></div>
              </div>
              <span class="font-bold text-green-600" x-text="formatCurrency(p.amount)"></span>
            </div>
          </template>
        </div>
      </div>

    </div>
  </div>
</div>
<script>
function platformDash() {
  return {
    data: null,
    async load() {
      if (!requireAuth()) return;
      const u = getUser();
      if (u.user_type !== 'PLATFORM_ADMIN') { location.href = '/pos'; return; }
      
      try {
        this.data = await apiFetch('/saas/admin/dashboard/');
      } catch(e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''
dash_path.write_text(dash_html.strip(), encoding="utf-8")
print("✅ Created platform_dashboard.html")

# ============================================================
# 4. Create the Applications UI
# ============================================================
apps_path = BACKEND_PATH / "templates" / "pos" / "platform_applications.html"
apps_html = '''
{% extends "pos/base.html" %}
{% block title %}Applications - Platform Admin{% endblock %}
{% block body %}
<div class="h-screen flex bg-slate-50">
  <!-- Include the same Sidebar as Dashboard -->
  <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col shadow-2xl z-20">
    <div class="h-16 flex items-center px-6 border-b border-slate-800 bg-slate-950/50">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center text-white shadow-lg"><i data-lucide="shield" class="w-5 h-5"></i></div>
        <div><div class="font-bold text-white tracking-wide text-lg">Nimbus HQ</div><div class="text-[10px] text-slate-400 uppercase tracking-wider">Platform Admin</div></div>
      </div>
    </div>
    <nav class="flex-1 py-6 px-4 space-y-1">
      <a href="/platform" class="nav-link"><i data-lucide="layout-dashboard" class="w-4 h-4 mr-3"></i> Overview</a>
      <a href="/platform/tenants" class="nav-link"><i data-lucide="building" class="w-4 h-4 mr-3"></i> Tenants</a>
      <a href="/platform/applications" class="nav-link active"><i data-lucide="file-text" class="w-4 h-4 mr-3"></i> Applications</a>
    </nav>
  </aside>

  <div class="flex-1 overflow-y-auto p-8" x-data="appsPage()" x-init="load()">
    <div class="flex justify-between items-center mb-8">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Signup Applications</h1>
        <p class="text-slate-500 mt-1">Review and approve new shops joining the platform.</p>
      </div>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-6 py-4">Business Name</th>
            <th class="px-6 py-4">Contact</th>
            <th class="px-6 py-4">Plan</th>
            <th class="px-6 py-4">Branches</th>
            <th class="px-6 py-4">Status</th>
            <th class="px-6 py-4 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="a in applications" :key="a.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-6 py-4 font-bold text-slate-900" x-text="a.business_name"></td>
              <td class="px-6 py-4">
                <div x-text="a.contact_name"></div>
                <div class="text-xs text-gray-500" x-text="a.contact_email"></div>
              </td>
              <td class="px-6 py-4"><span class="bg-indigo-50 text-indigo-700 px-2 py-1 rounded text-xs font-bold" x-text="a.plan || 'TRIAL'"></span></td>
              <td class="px-6 py-4" x-text="a.requested_branch_count"></td>
              <td class="px-6 py-4">
                <span class="px-2 py-1 rounded text-xs font-bold" 
                      :class="a.status === 'PENDING' ? 'bg-yellow-100 text-yellow-700' : a.status === 'APPROVED' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'" 
                      x-text="a.status"></span>
              </td>
              <td class="px-6 py-4 text-right">
                <button x-show="a.status === 'PENDING'" @click="approve(a.id)" class="btn-primary bg-green-600 hover:bg-green-700 text-xs px-3 py-1.5">Approve</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="applications.length === 0" class="p-8 text-center text-gray-400">No applications found.</div>
    </div>

    <!-- Success Modal -->
    <template x-if="credentials">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-8 shadow-2xl">
          <div class="text-center mb-6">
            <div class="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4"><i data-lucide="check" class="w-8 h-8"></i></div>
            <h2 class="text-2xl font-bold text-slate-900">Tenant Provisioned!</h2>
            <p class="text-sm text-gray-500 mt-1">Send these credentials to the business owner.</p>
          </div>
          <div class="bg-gray-50 p-4 rounded-lg space-y-3 font-mono text-sm border border-gray-200">
            <div><span class="text-gray-500 font-sans">Username:</span> <strong x-text="credentials.owner_username" class="text-slate-900"></strong></div>
            <div><span class="text-gray-500 font-sans">Password:</span> <strong x-text="credentials.owner_password" class="text-slate-900"></strong></div>
            <div><span class="text-gray-500 font-sans">Tenant Code:</span> <strong x-text="credentials.tenant_code" class="text-slate-900"></strong></div>
          </div>
          <button @click="credentials = null; load()" class="btn-primary w-full mt-6">Done</button>
        </div>
      </div>
    </template>
  </div>
</div>
<script>
function appsPage() {
  return {
    applications: [], credentials: null,
    async load() {
      if (!requireAuth()) return;
      if (getUser()?.user_type !== 'PLATFORM_ADMIN') { location.href = '/pos'; return; }
      try { this.applications = await apiFetch('/saas/applications/'); } catch(e) { alert(e.message); }
    },
    async approve(id) {
      if (!confirm('Approve this application and provision a new tenant?')) return;
      try {
        this.credentials = await apiFetch(`/saas/applications/${id}/approve/`, { method: 'POST' });
        setTimeout(() => { lucide.createIcons(); }, 50);
      } catch(e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
apps_path.write_text(apps_html.strip(), encoding="utf-8")
print("✅ Created platform_applications.html")

# ============================================================
# 5. Create the Tenants UI
# ============================================================
tenants_path = BACKEND_PATH / "templates" / "pos" / "platform_tenants.html"
tenants_html = '''
{% extends "pos/base.html" %}
{% block title %}Tenants - Platform Admin{% endblock %}
{% block body %}
<div class="h-screen flex bg-slate-50">
  <aside class="w-64 bg-slate-900 text-slate-300 flex flex-col shadow-2xl z-20">
    <div class="h-16 flex items-center px-6 border-b border-slate-800 bg-slate-950/50">
      <div class="flex items-center gap-3">
        <div class="w-8 h-8 rounded-lg bg-indigo-500 flex items-center justify-center text-white shadow-lg"><i data-lucide="shield" class="w-5 h-5"></i></div>
        <div><div class="font-bold text-white tracking-wide text-lg">Nimbus HQ</div><div class="text-[10px] text-slate-400 uppercase tracking-wider">Platform Admin</div></div>
      </div>
    </div>
    <nav class="flex-1 py-6 px-4 space-y-1">
      <a href="/platform" class="nav-link"><i data-lucide="layout-dashboard" class="w-4 h-4 mr-3"></i> Overview</a>
      <a href="/platform/tenants" class="nav-link active"><i data-lucide="building" class="w-4 h-4 mr-3"></i> Tenants</a>
      <a href="/platform/applications" class="nav-link"><i data-lucide="file-text" class="w-4 h-4 mr-3"></i> Applications</a>
    </nav>
  </aside>

  <div class="flex-1 overflow-y-auto p-8" x-data="tenantsPage()" x-init="load()">
    <div class="flex justify-between items-center mb-8">
      <div>
        <h1 class="text-2xl font-bold text-slate-900">Active Tenants</h1>
        <p class="text-slate-500 mt-1">Manage all businesses on the platform.</p>
      </div>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-6 py-4">Business</th>
            <th class="px-6 py-4">Plan</th>
            <th class="px-6 py-4">Status</th>
            <th class="px-6 py-4 text-center">Branches</th>
            <th class="px-6 py-4 text-center">Users</th>
            <th class="px-6 py-4 text-right">MRR</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="t in tenants" :key="t.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-6 py-4">
                <div class="font-bold text-slate-900" x-text="t.name"></div>
                <div class="text-xs text-gray-500" x-text="t.contact_email"></div>
              </td>
              <td class="px-6 py-4 font-medium" x-text="t.plan || 'Trial'"></td>
              <td class="px-6 py-4">
                <span class="px-2 py-1 rounded text-xs font-bold" 
                      :class="t.subscription_status === 'ACTIVE' ? 'bg-green-100 text-green-700' : t.subscription_status === 'TRIAL' ? 'bg-yellow-100 text-yellow-700' : 'bg-red-100 text-red-700'" 
                      x-text="t.subscription_status"></span>
              </td>
              <td class="px-6 py-4 text-center font-medium" x-text="t.branches_count"></td>
              <td class="px-6 py-4 text-center font-medium" x-text="t.users_count"></td>
              <td class="px-6 py-4 text-right font-bold text-green-600" x-text="formatCurrency(t.monthly_price)"></td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="tenants.length === 0" class="p-8 text-center text-gray-400">No tenants found.</div>
    </div>
  </div>
</div>
<script>
function tenantsPage() {
  return {
    tenants: [],
    async load() {
      if (!requireAuth()) return;
      if (getUser()?.user_type !== 'PLATFORM_ADMIN') { location.href = '/pos'; return; }
      try { this.tenants = await apiFetch('/saas/admin/tenants/'); } catch(e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''
tenants_path.write_text(tenants_html.strip(), encoding="utf-8")
print("✅ Created platform_tenants.html")

print("\n🎉 Done! Restart the server.")