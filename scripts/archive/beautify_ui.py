import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update base.html (Global Styles & Libraries)
# ============================================================
base_html = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}Nimbus POS{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: { 
        extend: { 
          colors: {
            brand: { 50:'#eef2ff', 100:'#e0e7ff', 500:'#6366f1', 600:'#4f46e5', 700:'#4338ca' }
          },
          fontFamily: {
            sans: ['Inter', 'ui-sans-serif', 'system-ui', '-apple-system', 'sans-serif'],
          }
        } 
      }
    }
  </script>
  <!-- Alpine.js -->
  <script defer src="https://unpkg.com/alpinejs@3.13.10/dist/cdn.min.js"></script>
  <!-- Lucide Icons -->
  <script src="https://unpkg.com/lucide@latest"></script>
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">

  <style>
    [x-cloak] { display: none !important; }
    body { font-family: 'Inter', sans-serif; background-color: #f8fafc; }
    
    /* Beautiful Inputs */
    .input-field { 
      width: 100%; padding: 0.6rem 0.875rem; border: 1px solid #e2e8f0; border-radius: 0.5rem; 
      font-size: 0.875rem; transition: all 0.2s; background-color: #ffffff;
    }
    .input-field:focus { 
      outline: none; border-color: #6366f1; box-shadow: 0 0 0 4px rgba(99,102,241,0.1); 
    }
    
    /* Polished Buttons */
    .btn-primary { 
      padding: 0.6rem 1.25rem; background: linear-gradient(to right, #4f46e5, #4338ca); 
      color: #ffffff; border-radius: 0.5rem; font-weight: 500; font-size: 0.875rem; 
      transition: all 0.2s; box-shadow: 0 2px 4px rgba(79,70,229,0.2); 
    }
    .btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 6px rgba(79,70,229,0.3); }
    .btn-primary:disabled { background: #cbd5e1; cursor: not-allowed; box-shadow: none; transform: none; }
    
    .btn-secondary { 
      padding: 0.6rem 1.25rem; background: #ffffff; color: #475569; border: 1px solid #e2e8f0; 
      border-radius: 0.5rem; font-weight: 500; font-size: 0.875rem; transition: all 0.2s; 
    }
    .btn-secondary:hover { background: #f8fafc; border-color: #cbd5e1; color: #1e293b; }
    
    /* Elegant Cards */
    .card { 
      background: #ffffff; border-radius: 0.75rem; border: 1px solid #e2e8f0; 
      box-shadow: 0 1px 3px rgba(0,0,0,0.02), 0 1px 2px rgba(0,0,0,0.04); 
    }
    
    /* Receipt Text */
    .receipt-text { font-family: 'Courier New', monospace; white-space: pre-wrap; font-size: 12px; line-height: 1.5; }
    
    /* Scrollbar */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: transparent; }
    ::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #94a3b8; }

    /* Animations */
    .fade-in { animation: fadeIn 0.3s ease-in-out; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(5px); } to { opacity: 1; transform: translateY(0); } }
  </style>
  
  <script src="/static/pos/api.js"></script>
  <script src="/static/pos/barcode.js" defer></script>
</head>
<body class="text-slate-800 antialiased">
  {% block body %}{% endblock %}
  <script>
    // Initialize Lucide icons on page load
    document.addEventListener('DOMContentLoaded', () => { lucide.createIcons(); });
  </script>
</body>
</html>
'''

# ============================================================
# 2. Update _nav.html (Sidebar UI)
# ============================================================
nav_html = '''
<aside class="w-64 bg-slate-900 text-slate-300 flex flex-col transition-all duration-300 shadow-2xl z-20 relative">
  <!-- Brand Header -->
  <div class="h-16 flex items-center px-6 border-b border-slate-800 bg-slate-950/50">
    <div class="flex items-center gap-3">
      <div class="w-8 h-8 rounded-lg bg-brand-600 flex items-center justify-center text-white shadow-lg">
        <i data-lucide="zap" class="w-5 h-5"></i>
      </div>
      <div>
        <div class="font-bold text-white tracking-wide text-lg">Nimbus POS</div>
        <div class="text-[10px] text-slate-400 uppercase tracking-wider" id="nav-tenant">Loading...</div>
      </div>
    </div>
  </div>

  <!-- Navigation Links -->
  <nav class="flex-1 py-6 px-4 space-y-1 overflow-y-auto">
    <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3 px-2">Store Operations</div>
    
    <a href="/pos" class="nav-link">
      <i data-lucide="shopping-cart" class="w-4 h-4 mr-3"></i> POS Checkout
    </a>
    <a href="/dashboard" class="nav-link" x-show="getUser()?.user_type !== 'SALES_AGENT'">
      <i data-lucide="layout-dashboard" class="w-4 h-4 mr-3"></i> Dashboard
    </a>
    <a href="/invoices" class="nav-link">
      <i data-lucide="file-text" class="w-4 h-4 mr-3"></i> Invoices
    </a>
    <a href="/returns" class="nav-link">
      <i data-lucide="rotate-ccw" class="w-4 h-4 mr-3"></i> Returns
    </a>
    <a href="/customers" class="nav-link">
      <i data-lucide="users" class="w-4 h-4 mr-3"></i> Customers
    </a>

    <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-6 mb-3 px-2">Inventory & Supply</div>
    
    <a href="/products" class="nav-link" x-show="getUser()?.user_type !== 'SALES_AGENT'">
      <i data-lucide="package" class="w-4 h-4 mr-3"></i> Products
    </a>
    <a href="/categories" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">
      <i data-lucide="grid" class="w-4 h-4 mr-3"></i> Categories
    </a>
    <a href="/stocktake" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">
      <i data-lucide="clipboard-list" class="w-4 h-4 mr-3"></i> Stock Take
    </a>
    <a href="/purchasing" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">
      <i data-lucide="truck" class="w-4 h-4 mr-3"></i> Purchasing
    </a>

    <div class="text-xs font-semibold text-slate-500 uppercase tracking-wider mt-6 mb-3 px-2">Management</div>
    
    <a href="/expenses" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">
      <i data-lucide="wallet" class="w-4 h-4 mr-3"></i> Expenses
    </a>
    <a href="/reports" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">
      <i data-lucide="bar-chart-2" class="w-4 h-4 mr-3"></i> Financial Reports
    </a>
    <a href="/accounting/coa" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">
      <i data-lucide="book" class="w-4 h-4 mr-3"></i> Chart of Accounts
    </a>
    <a href="/users" class="nav-link" x-show="getUser()?.user_type === 'TENANT_OWNER'">
      <i data-lucide="shield" class="w-4 h-4 mr-3"></i> User Management
    </a>
    <a href="/settings" class="nav-link" x-show="['TENANT_OWNER','MANAGER'].includes(getUser()?.user_type)">
      <i data-lucide="settings" class="w-4 h-4 mr-3"></i> Settings
    </a>
  </nav>

  <!-- User Profile Footer -->
  <div class="p-4 border-t border-slate-800 bg-slate-950/50">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-3">
        <div class="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center text-sm font-bold text-white">
          <span id="nav-user-initial">U</span>
        </div>
        <div class="overflow-hidden">
          <div class="text-sm font-medium text-white truncate" id="nav-user">User</div>
          <div class="text-[10px] text-brand-400 font-semibold uppercase" id="nav-role">Role</div>
        </div>
      </div>
      <button onclick="logout()" class="text-slate-400 hover:text-red-400 transition" title="Logout">
        <i data-lucide="log-out" class="w-5 h-5"></i>
      </button>
    </div>
  </div>
</aside>

<style>
  .nav-link { 
    display: flex; align-items: center; padding: 0.6rem 0.75rem; border-radius: 0.5rem; 
    font-size: 0.875rem; font-weight: 500; color: #94a3b8; transition: all 0.2s; 
  }
  .nav-link:hover { background: #1e293b; color: #f8fafc; }
  .nav-link.active { 
    background: linear-gradient(to right, rgba(79, 70, 229, 0.15), transparent);
    color: #818cf8; border-left: 3px solid #6366f1; border-radius: 0 0.5rem 0.5rem 0;
  }
</style>

<script>
  document.addEventListener('DOMContentLoaded', () => {
    const u = getUser();
    if (u) {
      document.getElementById('nav-user').textContent = u.username;
      document.getElementById('nav-user-initial').textContent = u.username.charAt(0).toUpperCase();
      document.getElementById('nav-role').textContent = u.user_type.replace('_', ' ');
    }
    const t = localStorage.getItem('tenant');
    if (t) document.getElementById('nav-tenant').textContent = t;

    // Highlight active link
    document.querySelectorAll('.nav-link').forEach((a) => {
      if (location.pathname.startsWith(a.getAttribute('href'))) {
        a.classList.add('active');
      }
    });
    
    // Refresh icons
    if (typeof lucide !== 'undefined') { lucide.createIcons(); }
  });
</script>
'''

# Overwrite the files
(Path(BACKEND_PATH) / "templates" / "pos" / "base.html").write_text(base_html.strip(), encoding="utf-8")
(Path(BACKEND_PATH) / "templates" / "pos" / "_nav.html").write_text(nav_html.strip(), encoding="utf-8")

print("✅ Rebuilt base.html (Global fonts, colors, icons)")
print("✅ Rebuilt _nav.html (Dark sidebar, icons, sections, active state)")

# ============================================================
# 3. Update Dashboard Header (Initiative Text)
# ============================================================
dash_path = BACKEND_PATH / "templates" / "pos" / "dashboard.html"
if dash_path.exists():
    d_content = dash_path.read_text(encoding="utf-8")
    
    # Update the header part
    old_header = '''    <div class="flex justify-between items-end mb-6">
      <div>
        <h1 class="text-2xl font-bold">Dashboard</h1>
        <p class="text-gray-500" x-text="branch + ' · ' + tenant"></p>
      </div>
      <div class="text-sm text-gray-500" x-text="'Last updated: ' + new Date().toLocaleTimeString()"></div>
    </div>'''
      
    new_header = '''    <div class="flex justify-between items-end mb-8 fade-in">
      <div>
        <h1 class="text-3xl font-bold text-slate-900 tracking-tight">Overview</h1>
        <p class="text-slate-500 mt-1 flex items-center gap-2">
          <i data-lucide="map-pin" class="w-4 h-4"></i> <span x-text="branch + ' · ' + tenant"></span>
        </p>
      </div>
      <div class="text-right">
        <div class="text-sm font-medium text-slate-500">System Time</div>
        <div class="text-lg font-bold text-brand-600" x-text="new Date().toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})"></div>
      </div>
    </div>'''
    
    if old_header in d_content:
        d_content = d_content.replace(old_header, new_header)
        dash_path.write_text(d_content, encoding="utf-8")
        print("✅ Updated Dashboard Header (Initiative Text)")

print("\n🎉 UI Beautification Complete! Refresh your browser to see the new look.")