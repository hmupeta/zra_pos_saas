import os
import subprocess
import sys

def run_cmd(cmd):
    print(f"⚙️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    return True

def write_file(path, content):
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📝 Updated: {path}")

def main():
    print("🚀 Starting Complete SaaS Architecture Implementation...")

    # 1. Update core/models.py for Finance Roles
    models_path = "core/models.py"
    if os.path.exists(models_path):
        with open(models_path, "r", encoding="utf-8") as f:
            content = f.read()
        if "ACCOUNTANT" not in content:
            # Try to safely inject the new choices
            if "'CASHIER', 'Cashier')," in content:
                content = content.replace("'CASHIER', 'Cashier'),", "'CASHIER', 'Cashier'),\n        ('ACCOUNTANT', 'Accountant'),\n        ('FINANCE_MANAGER', 'Finance Manager'),")
                write_file(models_path, content)
            else:
                print("⚠️ Could not automatically parse user_type choices. Please manually add 'ACCOUNTANT' and 'FINANCE_MANAGER' to core/models.py.")

    # 2. Create strict middleware
    middleware_content = """from django.http import JsonResponse
from core.models import BranchAccess

class StrictBranchMiddleware:
    \"\"\"Forces Cashiers and Managers to only access their assigned branch.\"\"\"
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.path.startswith('/api/') and request.user.is_authenticated:
            user = request.user
            
            # Owners and Admins can switch branches freely
            if user.user_type in ('TENANT_OWNER', 'PLATFORM_ADMIN') or user.is_superuser:
                return self.get_response(request)

            # For Cashiers, Managers, Finance, force their assigned branch
            if user.user_type in ('CASHIER', 'MANAGER', 'SALES_AGENT', 'ACCOUNTANT', 'FINANCE_MANAGER'):
                assigned_access = BranchAccess.objects.filter(user=user).first()
                if assigned_access:
                    # Overwrite whatever the frontend sent with the forced branch ID
                    request.META['HTTP_X_BRANCH_ID'] = str(assigned_access.company.id)
                else:
                    return JsonResponse({"error": "No branch assigned to your account. Contact your manager."}, status=403)

        return self.get_response(request)

class PlatformAdminIsolationMiddleware:
    \"\"\"Blocks Platform Admins from accessing tenant POS data.\"\"\"
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.user_type == 'PLATFORM_ADMIN':
            tenant_api_paths = ['/api/inventory/', '/api/sales/', '/api/customers/', '/api/payments/', '/api/pos/']
            if any(request.path.startswith(path) for path in tenant_api_paths):
                return JsonResponse({"error": "Platform Admins do not have access to tenant store data."}, status=403)
        return self.get_response(request)
"""
    write_file("core/middleware.py", middleware_content)

    # 3. Add Middleware to settings.py
    settings_path = "pos_backend/settings.py"
    with open(settings_path, "r", encoding="utf-8") as f:
        settings_content = f.read()
    
    if "StrictBranchMiddleware" not in settings_content:
        settings_content = settings_content.replace(
            "'subscriptions.middleware.TenantLimitMiddleware',",
            "'subscriptions.middleware.TenantLimitMiddleware',\n    'core.middleware.StrictBranchMiddleware',\n    'core.middleware.PlatformAdminIsolationMiddleware',"
        )
        write_file(settings_path, settings_content)

    # 4. Update _nav.html for Dynamic Sidebar
    nav_path = "templates/pos/_nav.html"
    nav_html = """
<aside class="w-64 bg-slate-900 text-slate-300 flex flex-col transition-all duration-300 shadow-2xl z-20 fixed top-0 left-0 h-screen">
  <div class="h-16 flex items-center px-6 border-b border-slate-800 bg-slate-950/50">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white shadow-lg"><i data-lucide="zap" class="w-5 h-5"></i></div>
      <div>
        <div class="font-bold text-white tracking-wide text-lg">Nimbus POS</div>
        <div class="text-[10px] text-slate-400 uppercase tracking-wider">{{ request.user.company.name|default:"Platform" }}</div>
      </div>
    </div>
  </div>

  <nav class="flex-1 py-6 px-4 space-y-1 overflow-y-auto">
    <!-- PLATFORM ADMIN ONLY -->
    {% if request.user.user_type == 'PLATFORM_ADMIN' %}
        <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 px-2">SaaS Management</div>
        <a href="/admin-dashboard" class="nav-link"><i data-lucide="layout-dashboard" class="w-4 h-4 mr-3"></i> Platform Dashboard</a>
        <a href="/admin-tenants" class="nav-link"><i data-lucide="store" class="w-4 h-4 mr-3"></i> Stores & Subscriptions</a>
    {% else %}
        <!-- TENANT USERS ONLY -->
        {% if request.user.user_type not in 'ACCOUNTANT,FINANCE_MANAGER' %}
            <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 px-2">Store Operations</div>
            <a href="/pos" class="nav-link"><i data-lucide="shopping-cart" class="w-4 h-4 mr-3"></i> POS Checkout</a>
            <a href="/dashboard" class="nav-link"><i data-lucide="layout-dashboard" class="w-4 h-4 mr-3"></i> Dashboard</a>
            <a href="/invoices" class="nav-link"><i data-lucide="file-text" class="w-4 h-4 mr-3"></i> Invoices</a>
            
            <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-6 mb-3 px-2">Inventory</div>
            <a href="/products" class="nav-link"><i data-lucide="package" class="w-4 h-4 mr-3"></i> Products</a>
        {% endif %}

        <!-- FINANCE & MANAGEMENT -->
        {% if request.user.user_type in 'TENANT_OWNER,MANAGER,ACCOUNTANT,FINANCE_MANAGER' %}
            <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-6 mb-3 px-2">Financial Management</div>
            <a href="/reports" class="nav-link"><i data-lucide="bar-chart-2" class="w-4 h-4 mr-3"></i> Financial Reports</a>
            <a href="/accounting/coa" class="nav-link"><i data-lucide="book" class="w-4 h-4 mr-3"></i> Chart of Accounts</a>
        {% endif %}
    {% endif %}
  </nav>

  <div class="p-4 border-t border-slate-800 bg-slate-950/50">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-sm font-bold text-white uppercase">{{ request.user.username|first|default:"U" }}</div>
        <div class="overflow-hidden">
          <div class="text-sm font-medium text-white truncate">{{ request.user.username|default:"User" }}</div>
          <div class="text-[10px] text-brand-400 font-semibold uppercase">{{ request.user.user_type|cut:"_"|default:"STAFF" }}</div>
        </div>
      </div>
      <button onclick="logout()" class="text-slate-400 hover:text-red-400 transition" title="Logout"><i data-lucide="log-out" class="w-5 h-5"></i></button>
    </div>
  </div>
</aside>

<style>
  .nav-link { display: flex; align-items: center; padding: 0.6rem 0.75rem; border-radius: 0.5rem; font-size: 0.875rem; font-weight: 500; color: #94a3b8; transition: all 0.2s; }
  .nav-link:hover { background: #1e293b; color: #f8fafc; }
</style>
"""
    write_file(nav_path, nav_html)

    # 5. Create Finance Users and Migrate
    print("\n🗄️ Running Migrations...")
    run_cmd("python manage.py makemigrations core")
    run_cmd("python manage.py migrate")

    print("\n👤 Creating Finance Users...")
    user_script = """
from django.contrib.auth import get_user_model
User = get_user_model()
admin = User.objects.get(username='admin')
c = admin.company
t = admin.tenant
User.objects.get_or_create(username='accountant1', defaults={'company': c, 'tenant': t, 'user_type': 'ACCOUNTANT'})
User.objects.get_or_create(username='finance1', defaults={'company': c, 'tenant': t, 'user_type': 'FINANCE_MANAGER'})
[u.set_password('Demo@123456') or u.save() for u in User.objects.filter(username__in=['accountant1', 'finance1'])]
print('✅ Finance users created!')
"""
    write_file("_temp_users.py", user_script)
    run_cmd("python manage.py shell < _temp_users.py")
    os.remove("_temp_users.py")

    # 6. Push to GitHub
    print("\n📤 Pushing to GitHub...")
    if run_cmd("git add ."):
        if run_cmd('git commit -m "Implement strict branch isolation, platform admin sandboxing, and finance roles"'):
            run_cmd("git push origin main")
            
    print("\n🎉 ALL DONE! Check your local app, then let Render deploy.")

if __name__ == "__main__":
    main()