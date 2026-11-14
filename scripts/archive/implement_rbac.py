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
# 1. Update User Roles in Models
# ============================================================
models_path = BACKEND_PATH / "core" / "models.py"
content = models_path.read_text(encoding="utf-8")
new_types = '''    USER_TYPES = [
        ("PLATFORM_ADMIN", "Platform Admin"),
        ("TENANT_OWNER", "Tenant Admin (Owner)"),
        ("MANAGER", "Manager"),
        ("SALES_ADMIN", "Sales Admin"),
        ("SALES_AGENT", "Sales Agent"),
    ]'''
content = re.sub(r"    USER_TYPES = \[.*?\]", new_types, content, flags=re.DOTALL)
models_path.write_text(content, encoding="utf-8")
print("✅ Updated User Roles in core/models.py")

# ============================================================
# 2. Enforce User Management (Tenant Admin Only)
# ============================================================
views_path = BACKEND_PATH / "core" / "views.py"
views_content = views_path.read_text(encoding="utf-8")

new_users_view = '''
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def users_list_create(request):
    # Only Tenant Owners can manage users
    if request.user.user_type != "TENANT_OWNER":
        return Response({"error": "Only Tenant Admins can manage users"}, status=403)

    if request.method == "GET":
        from django.contrib.auth import get_user_model
        User = get_user_model()
        users = User.objects.filter(tenant=request.tenant).order_by("-date_joined")
        return Response([{
            "id": u.id, "username": u.username, "email": u.email,
            "user_type": u.user_type, "is_active": u.is_active,
        } for u in users])

    data = request.data
    username = data.get("username")
    password = data.get("password")
    email = data.get("email", "")
    role = data.get("user_type", "SALES_AGENT")

    if not username or not password:
        return Response({"error": "Username and password required"}, status=400)

    from django.contrib.auth import get_user_model
    from django.db import transaction
    from core.models import BranchAccess, Company
    User = get_user_model()

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, email=email, password=password,
                tenant=request.tenant, user_type=role, employment_status="ACTIVE"
            )
            # Assign to current branch by default
            if request.branch:
                BranchAccess.objects.create(user=user, company=request.branch, is_default=True)
            return Response({"success": True, "id": user.id}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)
'''

# Replace the old users_list_create
views_content = re.sub(r"@api_view\(\[\"GET\", \"POST\"\]\).*?return Response\(\{\"error\": str\(e\)\}, status=500\)", new_users_view.strip(), views_content, flags=re.DOTALL)
views_path.write_text(views_content, encoding="utf-8")
print("✅ Enforced User Management (Tenant Owner Only) in core/views.py")

# ============================================================
# 3. Add Agent Performance Report & Void Sale Endpoint
# ============================================================
# Add Void Sale to sales/views.py
sales_views_path = BACKEND_PATH / "sales" / "views.py"
void_view = '''
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def void_invoice(request):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER", "SALES_ADMIN"):
        return Response({"error": "Only Managers or Sales Admins can void sales"}, status=403)
    invoice_id = request.data.get("invoice_id")
    try:
        invoice = Invoice.objects.get(pk=invoice_id, tenant=request.tenant)
        invoice.status = "VOID"
        invoice.save()
        return Response({"success": True})
    except Invoice.DoesNotExist:
        return Response({"error": "Not found"}, status=404)
'''
if "def void_invoice" not in sales_views_path.read_text(encoding="utf-8"):
    with open(sales_views_path, "a", encoding="utf-8") as f:
        f.write("\n\n" + void_view.strip())

# Add URL for void
sales_urls_path = BACKEND_PATH / "sales" / "urls.py"
url_content = sales_urls_path.read_text(encoding="utf-8")
if "void_invoice" not in url_content:
    url_content = url_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("invoices/void/", views.void_invoice, name="void_invoice"),'
    )
    sales_urls_path.write_text(url_content, encoding="utf-8")
print("✅ Added Void Sale Endpoint (Sales Admin+)")

# Add Agent Performance to reports/views.py
reports_views_path = BACKEND_PATH / "reports" / "views.py"
agent_perf_view = '''
from django.db.models import Sum, Count
from sales.models import Invoice

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def agent_performance(request):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Only Managers can view performance"}, status=403)
        
    # Group invoices by cashier
    perf = Invoice.objects.filter(tenant=request.tenant, status="PAID").values("cashier__username").annotate(
        total_sales=Sum("total"), 
        transaction_count=Count("id")
    ).order_by("-total_sales")
    
    return Response([{
        "agent": p["cashier__username"],
        "total_sales": float(p["total_sales"]),
        "transactions": p["transaction_count"]
    } for p in perf])
'''
if "def agent_performance" not in reports_views_path.read_text(encoding="utf-8"):
    with open(reports_views_path, "a", encoding="utf-8") as f:
        f.write("\n\n" + agent_perf_view.strip())

# Add URL for performance
reports_urls_path = BACKEND_PATH / "reports" / "urls.py"
r_url_content = reports_urls_path.read_text(encoding="utf-8")
if "agent_performance" not in r_url_content:
    r_url_content = r_url_content.replace(
        "urlpatterns = [",
        'urlpatterns = [\n    path("agent-performance/", views.agent_performance, name="agent_performance"),'
    )
    reports_urls_path.write_text(r_url_content, encoding="utf-8")
print("✅ Added Agent Performance Report (Manager+)")

# ============================================================
# 4. Frontend: Dynamic Navigation based on Roles
# ============================================================
nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")

new_nav = '''
<aside class="w-56 bg-white border-r border-gray-200 flex flex-col">
  <div class="p-4 border-b">
    <div class="font-bold text-lg text-brand-700">Nimbus POS</div>
    <div class="text-xs text-gray-500 truncate" id="nav-tenant"></div>
  </div>
  
  <nav class="flex-1 p-2 space-y-1" x-data>
    <a href="/pos" class="nav-link">POS</a>
    <a href="/dashboard" class="nav-link" x-show="getUser()?.user_type !== 'SALES_AGENT'">Dashboard</a>
    <a href="/products" class="nav-link" x-show="getUser()?.user_type !== 'SALES_AGENT'">Products</a>
    <a href="/invoices" class="nav-link">Invoices</a>
    <a href="/reports" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">Financial Reports</a>
    <a href="/users" class="nav-link" x-show="getUser()?.user_type === 'TENANT_OWNER'">User Management</a>
    <a href="/settings" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">Settings</a>
  </nav>
  
  <div class="p-3 border-t">
    <div class="text-xs text-gray-500">Signed in as</div>
    <div class="text-sm font-medium truncate" id="nav-user"></div>
    <div class="text-xs text-brand-600 font-semibold truncate" id="nav-role"></div>
    <button onclick="logout()" class="mt-2 text-xs text-red-600 hover:underline">Logout</button>
  </div>
</aside>
<style>
  .nav-link { display:block; padding:.5rem .75rem; border-radius:.5rem; font-size:.875rem; font-weight:500; color:#374151; }
  .nav-link:hover { background:#f3f4f6; }
  .nav-link.active { background:#eef2ff; color:#4338ca; }
</style>
<script>
  document.addEventListener('DOMContentLoaded', () => {
    const u = getUser();
    if (u) {
      document.getElementById('nav-user').textContent = u.username;
      // Format role nicely (SALES_ADMIN -> Sales Admin)
      document.getElementById('nav-role').textContent = u.user_type.replace('_', ' ').toLowerCase().replace(/\\b\\w/g, l => l.toUpperCase());
    }
    const t = localStorage.getItem('tenant');
    if (t) document.getElementById('nav-tenant').textContent = t;

    document.querySelectorAll('.nav-link').forEach((a) => {
      if (location.pathname === a.getAttribute('href')) a.classList.add('active');
    });
  });
</script>
'''
nav_path.write_text(new_nav.strip(), encoding="utf-8")
print("✅ Updated Navigation to hide menus based on Roles")

# ============================================================
# 5. Frontend: User Management Page
# ============================================================
users_html_path = BACKEND_PATH / "templates" / "pos" / "users.html"
new_users_html = '''
{% extends "pos/base.html" %}
{% block title %}Users{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="usersPage()" x-init="load()">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">User Management</h1>
      <button @click="showModal = true" class="btn-primary">+ Add User</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Username</th>
            <th class="px-4 py-3">Email</th>
            <th class="px-4 py-3">Role</th>
            <th class="px-4 py-3">Status</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="u in users" :key="u.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-medium" x-text="u.username"></td>
              <td class="px-4 py-3 text-gray-500" x-text="u.email || '-'"></td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded bg-blue-100 text-blue-800 text-xs" x-text="u.user_type"></span>
              </td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded text-xs" :class="u.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'" x-text="u.is_active ? 'Active' : 'Inactive'"></span>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Add User Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-md w-full p-6">
          <h2 class="text-xl font-bold mb-4">Add New User</h2>
          <form @submit.prevent="create()" class="space-y-3">
            <input placeholder="Username" x-model="form.username" class="input-field" required>
            <input type="email" placeholder="Email (optional)" x-model="form.email" class="input-field">
            <input type="password" placeholder="Password" x-model="form.password" class="input-field" required>
            
            <select x-model="form.user_type" class="input-field">
              <option value="SALES_AGENT">Sales Agent (Cashier)</option>
              <option value="SALES_ADMIN">Sales Admin (Can Void)</option>
              <option value="MANAGER">Manager (View Reports)</option>
            </select>

            <button type="submit" class="btn-primary w-full">Create User</button>
          </form>
        </div>
      </div>
    </template>
  </div>
</div>
<script>
function usersPage() {
  return {
    users: [], showModal: false,
    form: { username: '', email: '', password: '', user_type: 'SALES_AGENT' },
    async load() {
      if (!requireAuth()) return;
      try { this.users = await apiFetch('/auth/users/'); } catch(e) { alert(e.message); }
    },
    async create() {
      try {
        await apiFetch('/auth/users/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        this.form = { username: '', email: '', password: '', user_type: 'SALES_AGENT' };
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
users_html_path.write_text(new_users_html.strip(), encoding="utf-8")

# Add /users route to views_web.py and urls_web.py
views_web_path = BACKEND_PATH / "core" / "views_web.py"
views_web_content = views_web_path.read_text(encoding="utf-8")
if "def users_page" not in views_web_content:
    views_web_content += "\n\ndef users_page(request):\n    return render(request, 'pos/users.html')\n"
    views_web_path.write_text(views_web_content, encoding="utf-8")

urls_web_path = BACKEND_PATH / "core" / "urls_web.py"
urls_web_content = urls_web_path.read_text(encoding="utf-8")
if "/users" not in urls_web_content:
    urls_web_content = urls_web_content.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('users', views_web.users_page, name='users_page'),"
    )
    urls_web_path.write_text(urls_web_content, encoding="utf-8")
print("✅ Created User Management Frontend Page")

print("\n🎉 RBAC Complete! Restart server and refresh.")