"""
============================================================
POS FRONTEND — Django Templates (No Node, No Build)
============================================================
Serves the POS UI directly from Django.
  - Tailwind via CDN (no build)
  - Alpine.js via CDN (reactive, no build)
  - Vanilla JS fetch() for API calls
  - Django templates for structure

Usage:
    python build_pos_frontend_django.py

What you get:
  - Same UI as the React version, but served by Django
  - Single server (port 8000) — no proxy, no CORS
  - Works with your existing token auth
============================================================
"""

import os
import sys
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path.home() / "Documents" / "django" / "zra_pos_saas"


def get_python():
    venv = BACKEND_PATH / "venv"
    if platform.system() == "Windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def write_file(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content.strip() + "\n")
    print(f"  [WRITE] {path.relative_to(BACKEND_PATH)}")


def patch_file(path, old, new):
    with open(path, "r", encoding="utf-8") as f:
        content = f.read()
    if old not in content:
        print(f"  [SKIP] {path.name} — pattern not found")
        return False
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content.replace(old, new, 1))
    print(f"  [PATCH] {path.name}")
    return True


# ============================================================
# VIEWS
# ============================================================
VIEWS_WEB = '''
from django.shortcuts import render, redirect


def index(request):
    return redirect("/login")


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
'''


URLS_WEB = '''
from django.urls import path
from . import views_web

urlpatterns = [
    path("", views_web.index, name="index"),
    path("login", views_web.login_page, name="login_page"),
    path("select-branch", views_web.branch_select_page, name="branch_select_page"),
    path("pos", views_web.pos_page, name="pos_page"),
    path("dashboard", views_web.dashboard_page, name="dashboard_page"),
    path("products", views_web.products_page, name="products_page"),
    path("invoices", views_web.invoices_page, name="invoices_page"),
    path("reports", views_web.reports_page, name="reports_page"),
    path("settings", views_web.settings_page, name="settings_page"),
    path("admin", views_web.admin_dashboard_page, name="admin_dashboard_page"),
    path("admin/applications", views_web.admin_applications_page, name="admin_applications_page"),
    path("admin/tenants", views_web.admin_tenants_page, name="admin_tenants_page"),
    path("admin/plans", views_web.admin_plans_page, name="admin_plans_page"),
    path("admin/billing", views_web.admin_billing_page, name="admin_billing_page"),
]
'''


# ============================================================
# STATIC JS
# ============================================================
API_JS = '''
// Shared API wrapper
const API_BASE = '/api';

function getToken() { return localStorage.getItem('token'); }
function getBranchId() { return localStorage.getItem('branchId'); }
function getUser() {
  try { return JSON.parse(localStorage.getItem('user') || 'null'); }
  catch { return null; }
}

async function apiFetch(path, options = {}) {
  const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };
  const token = getToken();
  if (token) headers.Authorization = `Token ${token}`;
  const branchId = getBranchId();
  if (branchId) headers['X-Branch-ID'] = branchId;

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers });

  if (res.status === 401) {
    localStorage.clear();
    if (location.pathname !== '/login') location.href = '/login';
    throw new Error('Unauthorized');
  }

  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = new Error((data && data.error) || `HTTP ${res.status}`);
    err.response = { status: res.status, data };
    throw err;
  }
  return data;
}

function requireAuth() {
  if (!getToken()) { location.href = '/login'; return false; }
  return true;
}

function requireBranch() {
  if (!getBranchId()) { location.href = '/select-branch'; return false; }
  return true;
}

function requirePlatformAdmin() {
  const u = getUser();
  if (!u || u.user_type !== 'PLATFORM_ADMIN') { location.href = '/login'; return false; }
  return true;
}

function logout() {
  apiFetch('/auth/logout/', { method: 'POST' }).catch(() => {});
  localStorage.clear();
  location.href = '/login';
}

function formatCurrency(v) {
  return 'K' + parseFloat(v || 0).toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function formatDate(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}
'''


BARCODE_JS = '''
// Global HID keyboard-emulation barcode scanner.
// Fires a 'barcode-scanned' window event when a scan is detected.
(function () {
  let buffer = '';
  let lastKey = 0;

  document.addEventListener('keydown', (e) => {
    const t = e.target;
    const isFormField = ['INPUT', 'TEXTAREA', 'SELECT'].includes(t.tagName);
    if (isFormField && t.dataset.scanner !== 'true') return;

    const now = Date.now();
    if (now - lastKey > 100) buffer = '';
    lastKey = now;

    if (e.key === 'Enter') {
      const code = buffer.trim();
      buffer = '';
      if (code.length >= 4) {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent('barcode-scanned', { detail: { code } }));
      }
    } else if (/^[a-zA-Z0-9\\-_]$/.test(e.key)) {
      buffer += e.key;
    }
  });
})();

function printReceipt(text) {
  const esc = String(text).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
  const win = window.open('', '_blank', 'width=400,height=650');
  if (!win) { alert('Allow popups to print receipts'); return; }
  win.document.write(`
    <html><head><title>Receipt</title>
    <style>
      body { font-family: 'Courier New', monospace; font-size: 12px; margin: 8px; }
      pre { white-space: pre-wrap; word-wrap: break-word; margin: 0; }
      @media print { body { margin: 0; } }
    </style></head><body>
    <pre>${esc}</pre>
    <script>window.onload=()=>{window.print();setTimeout(()=>window.close(),100);}</script>
    </body></html>
  `);
  win.document.close();
}
'''


# ============================================================
# TEMPLATES
# ============================================================
BASE_TEMPLATE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{% block title %}POS{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script>
    tailwind.config = {
      theme: { extend: { colors: {
        brand: { 50:'#eef2ff',500:'#6366f1',600:'#4f46e5',700:'#4338ca' }
      } } }
    }
  </script>
  <script defer src="https://unpkg.com/alpinejs@3.13.10/dist/cdn.min.js"></script>
  <script src="https://unpkg.com/lucide@0.454.0/dist/umd/lucide.min.js"></script>
  <style>
    [x-cloak] { display: none !important; }
    html, body { height: 100%; }
    body { font-family: ui-sans-serif, system-ui, sans-serif; }
    .input-field { width:100%; padding:.5rem .75rem; border:1px solid #d1d5db; border-radius:.5rem; font-size:.875rem; }
    .input-field:focus { outline:none; border-color:#6366f1; box-shadow:0 0 0 3px rgba(99,102,241,.1); }
    .btn-primary { padding:.5rem 1rem; background:#4f46e5; color:#fff; border-radius:.5rem; font-weight:500; font-size:.875rem; }
    .btn-primary:hover { background:#4338ca; }
    .btn-primary:disabled { background:#d1d5db; cursor:not-allowed; }
    .btn-secondary { padding:.5rem 1rem; background:#fff; color:#374151; border:1px solid #d1d5db; border-radius:.5rem; font-weight:500; font-size:.875rem; }
    .btn-secondary:hover { background:#f9fafb; }
    .card { background:#fff; border-radius:.75rem; box-shadow:0 1px 2px rgba(0,0,0,.05); border:1px solid #f3f4f6; }
    .receipt-text { font-family:'Courier New',monospace; white-space:pre-wrap; font-size:12px; line-height:1.4; }
    .flash-green { animation:flash-g 0.6s ease-out; }
    @keyframes flash-g { 0% { background:#dcfce7; } 100% { background:transparent; } }
  </style>
  <script src="/static/pos/api.js"></script>
  <script src="/static/pos/barcode.js" defer></script>
</head>
<body class="bg-gray-50 text-gray-900">
  {% block body %}{% endblock %}
</body>
</html>
'''


NAV_TEMPLATE = '''
<aside class="w-56 bg-white border-r border-gray-200 flex flex-col">
  <div class="p-4 border-b">
    <div class="font-bold text-lg text-brand-700">POS</div>
    <div class="text-xs text-gray-500 truncate" id="nav-tenant"></div>
  </div>
  <nav class="flex-1 p-2 space-y-1">
    <a href="/pos"      class="nav-link">POS</a>
    <a href="/dashboard" class="nav-link">Dashboard</a>
    <a href="/products" class="nav-link">Products</a>
    <a href="/invoices" class="nav-link">Invoices</a>
    <a href="/reports"  class="nav-link">Reports</a>
    <a href="/settings" class="nav-link">Settings</a>
  </nav>
  <div class="p-3 border-t">
    <div class="text-xs text-gray-500">Signed in as</div>
    <div class="text-sm font-medium truncate" id="nav-user"></div>
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
    if (u) document.getElementById('nav-user').textContent = u.username;
    const t = localStorage.getItem('tenant');
    if (t) document.getElementById('nav-tenant').textContent = t;

    document.querySelectorAll('.nav-link').forEach((a) => {
      if (location.pathname === a.getAttribute('href')) a.classList.add('active');
    });
  });
</script>
'''


LOGIN_HTML = '''
{% extends "pos/base.html" %}
{% block title %}Login · POS{% endblock %}
{% block body %}
<div class="min-h-screen flex items-center justify-center bg-gradient-to-br from-indigo-50 to-indigo-100 p-4">
  <div class="w-full max-w-md bg-white rounded-2xl shadow-xl p-8" x-data="loginForm()">
    <div class="text-center mb-8">
      <h1 class="text-3xl font-bold text-brand-700">POS Login</h1>
      <p class="text-gray-500 mt-1 text-sm">Sign in to your store</p>
    </div>
    <form @submit.prevent="submit()" class="space-y-4">
      <div>
        <label class="block text-sm font-medium mb-1">Username</label>
        <input type="text" x-model="username" class="input-field" required autofocus>
      </div>
      <div>
        <label class="block text-sm font-medium mb-1">Password</label>
        <input type="password" x-model="password" class="input-field" required>
      </div>
      <p x-show="error" x-text="error" class="text-sm text-red-600"></p>
      <button type="submit" :disabled="loading" class="btn-primary w-full">
        <span x-show="!loading">Sign In</span>
        <span x-show="loading">Signing in...</span>
      </button>
    </form>
    <p class="text-xs text-gray-400 text-center mt-6">
      Demo: <code>demo_owner</code> / <code>Demo@123456</code> · Admin: <code>admin</code> / <code>Admin@123456</code>
    </p>
  </div>
</div>
<script>
function loginForm() {
  return {
    username: '', password: '', loading: false, error: '',
    async submit() {
      this.loading = true; this.error = '';
      try {
        const res = await apiFetch('/auth/login/', {
          method: 'POST',
          body: JSON.stringify({ username: this.username, password: this.password }),
        });
        localStorage.setItem('token', res.token);
        localStorage.setItem('user', JSON.stringify(res.user));
        if (res.tenant) localStorage.setItem('tenant', res.tenant);

        if (res.user.user_type === 'PLATFORM_ADMIN') {
          location.href = '/admin';
          return;
        }

        const branches = await apiFetch('/auth/branches/');
        if (branches.length === 0) {
          this.error = 'No branches assigned. Contact your administrator.';
          return;
        }
        if (branches.length === 1) {
          localStorage.setItem('branchId', branches[0].id);
          location.href = '/pos';
        } else {
          location.href = '/select-branch';
        }
      } catch (e) {
        this.error = e.response?.data?.error || 'Login failed';
      } finally {
        this.loading = false;
      }
    }
  }
}
</script>
{% endblock %}
'''


BRANCH_SELECT_HTML = '''
{% extends "pos/base.html" %}
{% block title %}Select Branch{% endblock %}
{% block body %}
<div class="min-h-screen flex items-center justify-center p-4 bg-gradient-to-br from-indigo-50 to-indigo-100">
  <div class="w-full max-w-2xl" x-data="branchPicker()" x-init="load()">
    <h1 class="text-2xl font-bold text-center mb-6">Select a branch</h1>
    <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <template x-for="b in branches" :key="b.id">
        <button @click="pick(b.id)" class="bg-white rounded-xl shadow-sm border p-6 text-left hover:shadow-lg hover:border-brand-500">
          <div class="text-lg font-semibold" x-text="b.name"></div>
          <div class="text-sm text-gray-500 mt-1">Code: <span x-text="b.code"></span></div>
          <div class="text-xs text-gray-400 mt-1">TPIN: <span x-text="b.tpin"></span></div>
        </button>
      </template>
    </div>
  </div>
</div>
<script>
function branchPicker() {
  return {
    branches: [],
    async load() {
      if (!requireAuth()) return;
      try { this.branches = await apiFetch('/auth/branches/'); }
      catch { alert('Failed to load branches'); }
    },
    pick(id) {
      localStorage.setItem('branchId', id);
      location.href = '/pos';
    }
  }
}
</script>
{% endblock %}
'''


POS_HTML = '''
{% extends "pos/base.html" %}
{% block title %}POS · Sale{% endblock %}
{% block body %}
<div class="h-screen flex" x-data="posScreen()" x-init="init()">

  <!-- Sidebar -->
  {% include "pos/_nav.html" %}

  <!-- Main -->
  <div class="flex-1 flex flex-col overflow-hidden">
    <header class="h-14 bg-white border-b flex items-center justify-between px-4">
      <div class="text-sm font-medium" id="pos-branch">Branch</div>
      <div class="text-xs px-2 py-1 rounded-full"
           :class="shift ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'"
           x-text="shift ? 'Scanner ready' : 'Shift closed'"></div>
    </header>

    <div class="flex-1 flex overflow-hidden">
      <!-- Products grid -->
      <div class="flex-1 p-4 overflow-y-auto">
        <div class="mb-4">
          <input type="text" x-model="search" placeholder="Search products or scan..."
                 class="input-field" />
        </div>
        <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          <template x-for="p in filteredProducts" :key="p.id">
            <button @click="scanAdd(p.barcode)"
                    :class="lastScan === p.barcode ? 'flash-green' : ''"
                    class="card p-3 text-left hover:shadow-md hover:border-brand-500 transition">
              <div class="font-medium text-sm line-clamp-2 h-10" x-text="p.name"></div>
              <div class="text-xs text-gray-500 mt-1" x-text="p.barcode"></div>
              <div class="flex justify-between items-end mt-2">
                <div class="text-lg font-bold text-brand-700" x-text="formatCurrency(p.selling_price)"></div>
                <div class="text-xs text-gray-400">Stock <span x-text="p.current_stock"></span></div>
              </div>
            </button>
          </template>
        </div>
        <div x-show="filteredProducts.length === 0" class="text-center py-12 text-gray-400">
          No products found
        </div>
      </div>

      <!-- Cart -->
      <div class="w-96 bg-white border-l flex flex-col">
        <div class="p-4 border-b flex justify-between items-center">
          <h2 class="font-semibold">Cart (<span x-text="cart.totals.item_count || 0"></span>)</h2>
          <button x-show="cart.items?.length > 0" @click="clearCart()" class="text-xs text-red-600">Clear</button>
        </div>
        <div class="flex-1 overflow-y-auto p-4 space-y-2">
          <template x-if="!cart.items || cart.items.length === 0">
            <div class="text-center py-12 text-gray-400">Scan or click products</div>
          </template>
          <template x-for="item in cart.items || []" :key="item.barcode">
            <div class="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
              <div class="flex-1 min-w-0">
                <div class="text-sm font-medium truncate" x-text="item.name"></div>
                <div class="text-xs text-gray-500">
                  <span x-text="formatCurrency(item.unit_price)"></span> × <span x-text="item.quantity"></span>
                </div>
              </div>
              <div class="text-sm font-semibold" x-text="formatCurrency(item.line_total)"></div>
            </div>
          </template>
        </div>
        <div class="p-4 border-t space-y-3">
          <div class="flex justify-between text-sm">
            <span class="text-gray-500">Subtotal</span>
            <span x-text="formatCurrency(cart.totals.subtotal || 0)"></span>
          </div>
          <div class="flex justify-between text-sm">
            <span class="text-gray-500">VAT</span>
            <span x-text="formatCurrency(cart.totals.tax_total || 0)"></span>
          </div>
          <div class="flex justify-between text-lg font-bold pt-2 border-t">
            <span>Total</span>
            <span class="text-brand-700" x-text="formatCurrency(cart.totals.total || 0)"></span>
          </div>
          <button :disabled="!shift || !cart.items || cart.items.length === 0"
                  @click="checkoutOpen = true" class="btn-primary w-full py-3 text-base">
            Checkout
          </button>
          <button x-show="shift" @click="closeShift()" class="btn-secondary w-full text-sm">
            Close Shift
          </button>
        </div>
      </div>
    </div>

    <!-- Open Shift Modal -->
    <div x-show="openShiftModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-md w-full p-6">
        <h2 class="text-xl font-bold mb-4">Open Shift</h2>
        <label class="block text-sm font-medium mb-1">Opening balance (cash in drawer)</label>
        <input type="number" x-model="openingBalance" class="input-field mb-4" />
        <button @click="openShift()" class="btn-primary w-full">Open Shift</button>
      </div>
    </div>

    <!-- Checkout Modal -->
    <div x-show="checkoutOpen" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-md w-full p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Checkout</h2>
          <button @click="checkoutOpen = false">✕</button>
        </div>
        <div class="text-center py-4 mb-4 bg-gray-50 rounded-lg">
          <div class="text-sm text-gray-500">Total to pay</div>
          <div class="text-3xl font-bold text-brand-700 mt-1" x-text="formatCurrency(cart.totals.total || 0)"></div>
        </div>
        <div class="space-y-2 mb-4">
          <template x-for="m in ['CASH','MOMO','CARD']" :key="m">
            <button @click="paymentMethod = m"
                    :class="paymentMethod === m ? 'border-brand-500 bg-brand-50' : 'border-gray-200'"
                    class="w-full flex items-center gap-3 px-4 py-3 rounded-lg border-2 transition">
              <span x-text="m === 'CASH' ? '💵 Cash' : m === 'MOMO' ? '📱 Mobile Money' : '💳 Card'"></span>
            </button>
          </template>
        </div>
        <button @click="doCheckout()" :disabled="busy" class="btn-primary w-full py-3 text-base">
          <span x-show="!busy">Pay <span x-text="formatCurrency(cart.totals.total || 0)"></span></span>
          <span x-show="busy">Processing...</span>
        </button>
      </div>
    </div>

    <!-- Receipt Modal -->
    <div x-show="receiptModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-md w-full max-h-[90vh] flex flex-col">
        <div class="p-4 border-b flex justify-between items-center">
          <h2 class="text-lg font-bold">Receipt</h2>
          <button @click="receiptModal = null">✕</button>
        </div>
        <div class="flex-1 overflow-y-auto p-4">
          <pre class="receipt-text bg-gray-50 p-4 rounded-lg" x-text="receiptModal?.text"></pre>
        </div>
        <div class="p-4 border-t flex gap-2">
          <button @click="printReceipt(receiptModal.text)" class="btn-secondary flex-1">Print</button>
          <button @click="receiptModal = null" class="btn-primary flex-1">Done</button>
        </div>
      </div>
    </div>

  </div>
</div>

<script>
function posScreen() {
  return {
    shift: null, products: [], cart: { items: [], totals: {} },
    search: '', busy: false, lastScan: null,
    openShiftModal: false, checkoutOpen: false, receiptModal: null,
    openingBalance: 0, paymentMethod: 'CASH',

    async init() {
      if (!requireAuth() || !requireBranch()) return;

      window.addEventListener('barcode-scanned', (e) => this.scanAdd(e.detail.code));

      try {
        this.shift = await apiFetch('/sales/current-shift/').catch((e) => {
          if (e.response?.status === 404) return null; throw e;
        });
        this.products = await apiFetch('/inventory/products/');

        if (this.shift) {
          this.cart = await apiFetch('/sales/cart/');
        } else {
          this.openShiftModal = true;
        }

        const branches = await apiFetch('/auth/branches/');
        const cur = branches.find(b => String(b.id) === String(getBranchId()));
        if (cur) document.getElementById('pos-branch').textContent = cur.name;
      } catch (e) {
        alert('Failed to load: ' + e.message);
      }
    },

    get filteredProducts() {
      const q = this.search.toLowerCase();
      return q
        ? this.products.filter(p => p.name.toLowerCase().includes(q) || p.barcode.includes(q))
        : this.products;
    },

    async scanAdd(barcode) {
      if (!this.shift) { alert('Open a shift first'); return; }
      try {
        const res = await apiFetch('/sales/scan-add/', {
          method: 'POST',
          body: JSON.stringify({ barcode, quantity: 1 }),
        });
        this.cart = res.cart;
        this.lastScan = res.product.barcode;
        setTimeout(() => this.lastScan = null, 700);
      } catch (e) {
        alert(e.response?.data?.error || 'Scan failed');
      }
    },

    async openShift() {
      try {
        await apiFetch('/sales/open-shift/', {
          method: 'POST',
          body: JSON.stringify({ opening_balance: parseFloat(this.openingBalance) || 0 }),
        });
        this.shift = await apiFetch('/sales/current-shift/');
        this.openShiftModal = false;
      } catch (e) {
        alert(e.response?.data?.error || 'Failed');
      }
    },

    async closeShift() {
      if (!confirm('Close this shift?')) return;
      try {
        await apiFetch('/sales/close-shift/', { method: 'POST' });
        this.shift = null;
        this.cart = { items: [], totals: {} };
        this.openShiftModal = true;
      } catch (e) { alert('Failed'); }
    },

    async clearCart() {
      if (!confirm('Clear cart?')) return;
      try {
        await apiFetch('/sales/cart/clear/', { method: 'POST' });
        this.cart = { items: [], totals: {} };
      } catch (e) { alert('Failed'); }
    },

    async doCheckout() {
      this.busy = true;
      try {
        const res = await apiFetch('/sales/cart/checkout/', {
          method: 'POST',
          body: JSON.stringify({ payment_method: this.paymentMethod }),
        });
        const receipt = await apiFetch(`/sales/invoices/${res.invoice_id}/receipt.txt`);
        this.receiptModal = { ...res, text: receipt.text };
        this.cart = { items: [], totals: {} };
        this.checkoutOpen = false;
        this.paymentMethod = 'CASH';
      } catch (e) {
        alert(e.response?.data?.error || 'Checkout failed');
      } finally {
        this.busy = false;
      }
    },
  }
}
</script>
{% endblock %}
'''


DASHBOARD_HTML = '''
{% extends "pos/base.html" %}
{% block title %}Dashboard{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="dashboard()" x-init="load()">
    <h1 class="text-2xl font-bold mb-1">Dashboard</h1>
    <p class="text-gray-500 mb-6" x-text="branch + ' · ' + tenant"></p>
    <div class="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
      <template x-for="k in kpis" :key="k.label">
        <div class="card p-5">
          <div class="text-sm text-gray-500" x-text="k.label"></div>
          <div class="text-2xl font-bold mt-1" x-text="k.value"></div>
        </div>
      </template>
    </div>
    <div class="card p-6" x-show="summary">
      <h2 class="font-semibold mb-4">Last 7 Days</h2>
      <div class="grid grid-cols-3 gap-4">
        <div>
          <div class="text-sm text-gray-500">Total Sales</div>
          <div class="text-xl font-bold" x-text="formatCurrency(summary?.total_sales)"></div>
        </div>
        <div>
          <div class="text-sm text-gray-500">Transactions</div>
          <div class="text-xl font-bold" x-text="summary?.transaction_count"></div>
        </div>
        <div>
          <div class="text-sm text-gray-500">VAT Collected</div>
          <div class="text-xl font-bold" x-text="formatCurrency(summary?.total_tax)"></div>
        </div>
      </div>
    </div>
  </div>
</div>
<script>
function dashboard() {
  return {
    branch: '', tenant: '', kpis: [], summary: null,
    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try {
        const d = await apiFetch('/reports/dashboard/');
        this.branch = d.branch || '';
        this.tenant = d.tenant || '';
        this.kpis = [
          { label: "Today's Sales", value: formatCurrency(d.today_sales) },
          { label: 'Transactions', value: d.today_transactions },
          { label: 'Total Products', value: d.total_products },
          { label: 'Low Stock', value: d.low_stock },
        ];
        this.summary = await apiFetch('/reports/sales-summary/?period=week');
      } catch (e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''


PRODUCTS_HTML = '''
{% extends "pos/base.html" %}
{% block title %}Products{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="productsPage()" x-init="load()">
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Products</h1>
      <button @click="showModal = true" class="btn-primary">+ Add Product</button>
    </div>
    <input type="text" x-model="search" placeholder="Search..." class="input-field mb-4 max-w-sm" />
    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Barcode</th>
            <th class="px-4 py-3">Name</th>
            <th class="px-4 py-3 text-right">Price</th>
            <th class="px-4 py-3 text-right">Stock</th>
            <th class="px-4 py-3 text-right">VAT</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="p in filtered" :key="p.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-mono text-xs" x-text="p.barcode"></td>
              <td class="px-4 py-3 font-medium" x-text="p.name"></td>
              <td class="px-4 py-3 text-right" x-text="formatCurrency(p.selling_price)"></td>
              <td class="px-4 py-3 text-right" x-text="p.current_stock"></td>
              <td class="px-4 py-3 text-right text-gray-500"><span x-text="p.tax_rate"></span>%</td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="filtered.length === 0" class="p-8 text-center text-gray-400">No products</div>
    </div>

    <div x-show="showModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-lg w-full p-6">
        <div class="flex justify-between items-center mb-4">
          <h2 class="text-xl font-bold">Add Product</h2>
          <button @click="showModal = false">✕</button>
        </div>
        <form @submit.prevent="create()" class="space-y-3">
          <input v placeholder="Barcode" x-model="form.barcode" class="input-field" required>
          <input placeholder="Name" x-model="form.name" class="input-field" required>
          <div class="grid grid-cols-2 gap-3">
            <input type="number" step="0.01" placeholder="Selling price" x-model="form.selling_price" class="input-field" required>
            <input type="number" step="0.01" placeholder="Cost" x-model="form.unit_cost" class="input-field">
          </div>
          <div class="grid grid-cols-2 gap-3">
            <input type="number" step="0.01" placeholder="Stock" x-model="form.current_stock" class="input-field">
            <input placeholder="ZRA item code" x-model="form.zra_item_code" class="input-field">
          </div>
          <div class="grid grid-cols-2 gap-3">
            <input type="number" placeholder="Category ID" x-model="form.category_id" class="input-field">
            <input type="number" placeholder="Tax rate ID" x-model="form.tax_rate_id" class="input-field">
          </div>
          <button type="submit" class="btn-primary w-full">Create Product</button>
        </form>
      </div>
    </div>
  </div>
</div>
<script>
function productsPage() {
  return {
    products: [], search: '', showModal: false,
    form: { barcode:'', name:'', selling_price:'', unit_cost:'0',
            current_stock:'0', category_id:1, tax_rate_id:1, zra_item_code:'' },
    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try { this.products = await apiFetch('/inventory/products/'); }
      catch (e) { alert(e.message); }
    },
    get filtered() {
      const q = this.search.toLowerCase();
      return q ? this.products.filter(p => p.name.toLowerCase().includes(q) || p.barcode.includes(q)) : this.products;
    },
    async create() {
      try {
        await apiFetch('/inventory/products/', {
          method: 'POST',
          body: JSON.stringify({
            ...this.form,
            selling_price: parseFloat(this.form.selling_price),
            unit_cost: parseFloat(this.form.unit_cost || 0),
            current_stock: parseFloat(this.form.current_stock || 0),
            category_id: parseInt(this.form.category_id),
            tax_rate_id: parseInt(this.form.tax_rate_id),
          }),
        });
        this.showModal = false;
        this.form = { barcode:'', name:'', selling_price:'', unit_cost:'0',
                      current_stock:'0', category_id:1, tax_rate_id:1, zra_item_code:'' };
        await this.load();
      } catch (e) { alert(e.response?.data?.error || 'Failed'); }
    }
  }
}
</script>
{% endblock %}
'''


INVOICES_HTML = '''
{% extends "pos/base.html" %}
{% block title %}Invoices{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="invoicesPage()" x-init="load()">
    <h1 class="text-2xl font-bold mb-6">Invoices</h1>
    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Invoice #</th>
            <th class="px-4 py-3">Date</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3 text-right">Total</th>
            <th class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="inv in invoices" :key="inv.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-mono text-xs" x-text="inv.invoice_number"></td>
              <td class="px-4 py-3" x-text="formatDate(inv.created_at)"></td>
              <td class="px-4 py-3">
                <span :class="inv.status === 'PAID' ? 'bg-green-100 text-green-700' : 'bg-yellow-100 text-yellow-700'"
                      class="px-2 py-0.5 rounded-full text-xs" x-text="inv.status"></span>
              </td>
              <td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(inv.total)"></td>
              <td class="px-4 py-3 text-right">
                <button @click="printReceiptFor(inv.id)" class="text-xs text-brand-600 hover:underline">Print</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      <div x-show="invoices.length === 0" class="p-8 text-center text-gray-400">No invoices yet</div>
    </div>
  </div>
</div>
<script>
function invoicesPage() {
  return {
    invoices: [],
    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try { this.invoices = await apiFetch('/sales/invoices/'); }
      catch (e) { alert(e.message); }
    },
    async printReceiptFor(id) {
      try {
        const r = await apiFetch(`/sales/invoices/${id}/receipt.txt`);
        printReceipt(r.text);
      } catch (e) { alert('Failed to load receipt'); }
    }
  }
}
</script>
{% endblock %}
'''


REPORTS_HTML = '''
{% extends "pos/base.html" %}
{% block title %}Reports{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="reportsPage()" x-init="load('trial')">
    <h1 class="text-2xl font-bold mb-6">Financial Reports</h1>
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
            <tr class="border-t">
              <td class="px-4 py-2 font-mono text-xs" x-text="a.code"></td>
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
    </div>

    <!-- Balance Sheet -->
    <div x-show="tab === 'balance' && data" class="grid grid-cols-1 md:grid-cols-2 gap-4">
      <div class="card p-6">
        <h2 class="font-semibold mb-4">Assets</h2>
        <div class="text-2xl font-bold text-green-700" x-text="formatCurrency(data?.assets)"></div>
      </div>
      <div class="card p-6">
        <h2 class="font-semibold mb-4">Liabilities & Equity</h2>
        <div class="space-y-2 text-sm">
          <div class="flex justify-between"><span>Liabilities</span><span x-text="formatCurrency(data?.liabilities)"></span></div>
          <div class="flex justify-between"><span>Equity</span><span x-text="formatCurrency(data?.equity)"></span></div>
          <div class="flex justify-between"><span>Net Income</span><span x-text="formatCurrency(data?.net_income)"></span></div>
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
    tab: 'trial', data: null,
    async load(tabId) {
      if (!requireAuth() || !requireBranch()) return;
      this.tab = tabId; this.data = null;
      const ep = {
        trial: '/accounting/reports/trial-balance/',
        balance: '/accounting/reports/balance-sheet/',
        income: '/accounting/reports/income-statement/',
      }[tabId];
      try { this.data = await apiFetch(ep); }
      catch (e) { alert(e.message); }
    }
  }
}
</script>
{% endblock %}
'''


SETTINGS_HTML = '''
{% extends "pos/base.html" %}
{% block title %}Settings{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="settingsPage()" x-init="load()">
    <h1 class="text-2xl font-bold mb-6">Settings</h1>
    <div class="card p-6">
      <div class="flex justify-between items-center mb-4">
        <h2 class="font-semibold">Payment Gateways (this branch)</h2>
        <button @click="showModal = true" class="btn-primary text-sm">Add Config</button>
      </div>
      <template x-if="configs.length === 0">
        <div class="text-gray-400 text-sm">No payment gateways configured</div>
      </template>
      <div class="space-y-2">
        <template x-for="c in configs" :key="c.id">
          <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
            <div>
              <div class="font-medium" x-text="c.provider"></div>
              <div class="text-xs text-gray-500">
                Merchant: <span x-text="c.merchant_id || '-'"></span>
                <span x-show="c.is_default"> · Default</span>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>

    <div x-show="showModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-md w-full p-6">
        <h2 class="text-xl font-bold mb-4">Add Payment Config</h2>
        <form @submit.prevent="save()" class="space-y-3">
          <select x-model="form.provider" class="input-field">
            <option value="MONEYUNIFY">MoneyUnify</option>
            <option value="MTN_DIRECT">MTN Direct</option>
            <option value="AIRTEL_DIRECT">Airtel Direct</option>
          </select>
          <input placeholder="Merchant ID" x-model="form.merchant_id" class="input-field" required>
          <input placeholder="API Key" x-model="form.api_key" class="input-field">
          <label class="flex items-center gap-2 text-sm">
            <input type="checkbox" x-model="form.is_default"> Set as default
          </label>
          <button type="submit" class="btn-primary w-full">Save</button>
        </form>
      </div>
    </div>
  </div>
</div>
<script>
function settingsPage() {
  return {
    configs: [], showModal: false,
    form: { provider: 'MONEYUNIFY', merchant_id: '', api_key: '', is_default: true },
    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try { this.configs = await apiFetch('/payments/configs/'); }
      catch (e) { console.error(e); }
    },
    async save() {
      try {
        await apiFetch('/payments/configs/', {
          method: 'POST',
          body: JSON.stringify(this.form),
        });
        this.showModal = false;
        await this.load();
      } catch (e) { alert(e.response?.data?.error || 'Failed'); }
    }
  }
}
</script>
{% endblock %}
'''


# ============================================================
# ADMIN TEMPLATES
# ============================================================
ADMIN_BASE = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{% block title %}Admin · POS{% endblock %}</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://unpkg.com/alpinejs@3.13.10/dist/cdn.min.js"></script>
  <style>[x-cloak]{display:none!important}</style>
  <style>
    .input-field { width:100%; padding:.5rem .75rem; border:1px solid #d1d5db; border-radius:.5rem; font-size:.875rem; }
    .btn-primary { padding:.5rem 1rem; background:#4f46e5; color:#fff; border-radius:.5rem; font-weight:500; font-size:.875rem; }
    .btn-primary:hover { background:#4338ca; }
    .btn-primary:disabled { background:#d1d5db; cursor:not-allowed; }
    .btn-secondary { padding:.5rem 1rem; background:#fff; border:1px solid #d1d5db; border-radius:.5rem; font-weight:500; font-size:.875rem; }
    .card { background:#fff; border-radius:.75rem; box-shadow:0 1px 2px rgba(0,0,0,.05); border:1px solid #f3f4f6; }
  </style>
  <script src="/static/pos/api.js"></script>
</head>
<body class="bg-gray-50">
<div class="min-h-screen flex">
  <aside class="w-60 bg-slate-900 text-slate-100 flex flex-col">
    <div class="p-5 border-b border-slate-800">
      <div class="font-bold">Platform Admin</div>
      <div class="text-xs text-slate-400 mt-1 truncate" id="nav-user"></div>
    </div>
    <nav class="flex-1 p-3 space-y-1" id="admin-nav">
      <a href="/admin"              class="admin-link">Dashboard</a>
      <a href="/admin/applications" class="admin-link">Applications <span id="app-badge" class="hidden ml-auto bg-red-500 text-white text-xs px-1.5 py-0.5 rounded-full"></span></a>
      <a href="/admin/tenants"      class="admin-link">Tenants</a>
      <a href="/admin/plans"        class="admin-link">Plans</a>
      <a href="/admin/billing"      class="admin-link">Billing</a>
    </nav>
    <div class="p-3 border-t border-slate-800">
      <button onclick="logout()" class="text-sm text-slate-300 hover:text-white">Logout</button>
    </div>
  </aside>
  <main class="flex-1 overflow-y-auto">{% block content %}{% endblock %}</main>
</div>
<style>
  .admin-link { display:flex; align-items:center; gap:.5rem; padding:.5rem .75rem; border-radius:.5rem; font-size:.875rem; color:#cbd5e1; }
  .admin-link:hover { background:#1e293b; }
  .admin-link.active { background:#4f46e5; color:#fff; }
</style>
<script>
  document.addEventListener('DOMContentLoaded', () => {
    if (!requirePlatformAdmin()) return;
    const u = getUser();
    if (u) document.getElementById('nav-user').textContent = u.username;
    document.querySelectorAll('.admin-link').forEach((a) => {
      if (location.pathname === a.getAttribute('href')) a.classList.add('active');
    });
    apiFetch('/saas/admin/dashboard/').then(d => {
      const n = d.kpis.pending_applications;
      if (n > 0) {
        const b = document.getElementById('app-badge');
        b.textContent = n;
        b.classList.remove('hidden');
      }
    }).catch(() => {});
  });
</script>
</body>
</html>
'''


ADMIN_DASHBOARD = '''
{% extends "pos/admin/base.html" %}
{% block title %}Admin Dashboard{% endblock %}
{% block content %}
<div class="p-6" x-data="adminDash()" x-init="load()">
  <h1 class="text-2xl font-bold mb-6">Platform Overview</h1>
  <template x-if="!data"><div class="text-gray-500">Loading...</div></template>
  <template x-if="data">
    <div>
      <div class="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4 mb-6">
        <template x-for="k in kpis" :key="k.label">
          <div class="card p-4">
            <div class="text-xs text-gray-500" x-text="k.label"></div>
            <div class="text-lg font-bold" x-text="k.value"></div>
          </div>
        </template>
      </div>
      <div class="bg-red-50 border border-red-200 rounded-xl p-4 mb-6">
        <div class="text-sm text-red-800">
          <strong>Outstanding billing:</strong>
          <span x-text="formatCurrency(data.kpis.outstanding_balance)"></span> —
          <a href="/admin/billing" class="underline">View invoices</a>
        </div>
      </div>
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <div class="card p-5">
          <div class="flex justify-between items-center mb-3">
            <h2 class="font-semibold">Recent Signups</h2>
            <a href="/admin/applications" class="text-sm text-indigo-600">View all →</a>
          </div>
          <template x-if="data.recent_signups.length === 0">
            <div class="text-sm text-gray-400">None yet</div>
          </template>
          <template x-for="s in data.recent_signups" :key="s.id">
            <div class="flex justify-between items-center p-2 bg-gray-50 rounded-lg mb-2">
              <div>
                <div class="text-sm font-medium" x-text="s.business_name"></div>
                <div class="text-xs text-gray-500" x-text="s.contact_email"></div>
              </div>
              <span class="text-xs px-2 py-0.5 rounded-full bg-yellow-100 text-yellow-700" x-text="s.status"></span>
            </div>
          </template>
        </div>
        <div class="card p-5">
          <div class="flex justify-between items-center mb-3">
            <h2 class="font-semibold">Recent Payments</h2>
            <a href="/admin/billing" class="text-sm text-indigo-600">View all →</a>
          </div>
          <template x-if="data.recent_payments.length === 0">
            <div class="text-sm text-gray-400">None yet</div>
          </template>
          <template x-for="p in data.recent_payments" :key="p.id">
            <div class="flex justify-between items-center p-2 bg-gray-50 rounded-lg mb-2">
              <div>
                <div class="text-sm font-medium" x-text="p.tenant_name"></div>
                <div class="text-xs text-gray-500" x-text="p.payment_date"></div>
              </div>
              <div class="text-sm font-bold text-green-700" x-text="formatCurrency(p.amount)"></div>
            </div>
          </template>
        </div>
      </div>
    </div>
  </template>
</div>
<script>
function adminDash() {
  return {
    data: null, kpis: [],
    async load() {
      this.data = await apiFetch('/saas/admin/dashboard/');
      const k = this.data.kpis;
      this.kpis = [
        { label: 'MRR', value: formatCurrency(k.mrr) },
        { label: 'ARR', value: formatCurrency(k.arr) },
        { label: 'Active Tenants', value: k.active_tenants },
        { label: 'Trial Tenants', value: k.trial_tenants },
        { label: 'Pending Signups', value: k.pending_applications },
        { label: 'Renewals (30d)', value: k.upcoming_renewals_30d },
      ];
    }
  }
}
</script>
{% endblock %}
'''


ADMIN_APPLICATIONS = '''
{% extends "pos/admin/base.html" %}
{% block title %}Applications{% endblock %}
{% block content %}
<div class="p-6" x-data="appsPage()" x-init="load()">
  <h1 class="text-2xl font-bold mb-6">Signup Applications</h1>
  <div class="flex gap-2 mb-4">
    <template x-for="f in ['PENDING','APPROVED','REJECTED','INFO_REQUIRED','']" :key="f">
      <button @click="filter = f; load()"
              :class="filter === f ? 'bg-indigo-600 text-white' : 'bg-white border'"
              class="px-3 py-1.5 text-sm rounded-lg" x-text="f || 'All'"></button>
    </template>
  </div>

  <div class="card overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
        <tr>
          <th class="px-4 py-3">Business</th>
          <th class="px-4 py-3">Contact</th>
          <th class="px-4 py-3">Plan</th>
          <th class="px-4 py-3">Submitted</th>
          <th class="px-4 py-3">Status</th>
          <th class="px-4 py-3 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        <template x-for="a in apps" :key="a.id">
          <tr class="border-t hover:bg-gray-50">
            <td class="px-4 py-3 font-medium" x-text="a.business_name"></td>
            <td class="px-4 py-3">
              <div x-text="a.contact_name"></div>
              <div class="text-xs text-gray-500" x-text="a.contact_email"></div>
              <div class="text-xs text-gray-500" x-text="a.contact_phone"></div>
            </td>
            <td class="px-4 py-3" x-text="a.plan || '-'"></td>
            <td class="px-4 py-3 text-gray-500" x-text="formatDate(a.submitted_at)"></td>
            <td class="px-4 py-3">
              <span class="px-2 py-0.5 rounded-full text-xs"
                    :class="{
                      'bg-yellow-100 text-yellow-700': a.status === 'PENDING',
                      'bg-green-100 text-green-700': a.status === 'APPROVED',
                      'bg-red-100 text-red-700': a.status === 'REJECTED',
                      'bg-blue-100 text-blue-700': a.status === 'INFO_REQUIRED'
                    }" x-text="a.status"></span>
            </td>
            <td class="px-4 py-3 text-right">
              <template x-if="a.status === 'PENDING'">
                <div class="flex justify-end gap-1">
                  <button @click="approve(a.id)" class="px-2 py-1 text-xs bg-green-100 text-green-700 rounded">Approve</button>
                  <button @click="reject(a.id)" class="px-2 py-1 text-xs bg-red-100 text-red-700 rounded">Reject</button>
                </div>
              </template>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <div x-show="apps.length === 0" class="p-8 text-center text-gray-400">No applications</div>
  </div>

  <template x-if="credentials">
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-md w-full p-6">
        <h2 class="text-xl font-bold mb-3 text-green-700">✓ Tenant Provisioned</h2>
        <div class="bg-gray-50 p-4 rounded-lg space-y-2 mb-4 text-sm">
          <div><strong>Tenant:</strong> <span x-text="credentials.tenant_code"></span></div>
          <div><strong>Username:</strong> <code x-text="credentials.owner_username"></code></div>
          <template x-if="credentials.owner_password">
            <div><strong>Password:</strong> <code x-text="credentials.owner_password"></code></div>
          </template>
          <div><strong>Trial ends:</strong> <span x-text="formatDate(credentials.trial_ends_at)"></span></div>
        </div>
        <p class="text-sm text-gray-600 mb-4">Share with the customer. Password won't be shown again.</p>
        <button @click="copyCreds()" class="btn-primary w-full mb-2">Copy Credentials</button>
        <button @click="credentials = null" class="btn-secondary w-full">Done</button>
      </div>
    </div>
  </template>
</div>
<script>
function appsPage() {
  return {
    apps: [], filter: 'PENDING', credentials: null,
    async load() {
      const q = this.filter ? `?status=${this.filter}` : '';
      this.apps = await apiFetch(`/saas/applications/${q}`);
    },
    async approve(id) {
      if (!confirm('Approve and provision tenant?')) return;
      try {
        this.credentials = await apiFetch(`/saas/applications/${id}/approve/`, { method: 'POST' });
        await this.load();
      } catch (e) { alert(e.response?.data?.error || 'Failed'); }
    },
    async reject(id) {
      const reason = prompt('Reason for rejection?');
      if (!reason) return;
      try {
        await apiFetch(`/saas/applications/${id}/reject/`, {
          method: 'POST',
          body: JSON.stringify({ reason }),
        });
        await this.load();
      } catch (e) { alert('Failed'); }
    },
    copyCreds() {
      const c = this.credentials;
      const text = `Username: ${c.owner_username}\nPassword: ${c.owner_password || ''}\nTenant: ${c.tenant_code}\nTrial ends: ${c.trial_ends_at}`;
      navigator.clipboard.writeText(text).then(() => alert('Copied'));
    }
  }
}
</script>
{% endblock %}
'''


ADMIN_TENANTS = '''
{% extends "pos/admin/base.html" %}
{% block title %}Tenants{% endblock %}
{% block content %}
<div class="p-6" x-data="tenantsPage()" x-init="load()">
  <h1 class="text-2xl font-bold mb-6">Tenants</h1>
  <div class="flex gap-2 mb-4">
    <input type="text" x-model="search" @input="load()" placeholder="Search..." class="input-field max-w-sm">
    <select x-model="filter" @change="load()" class="input-field w-40">
      <option value="">All</option>
      <option value="TRIAL">Trial</option>
      <option value="ACTIVE">Active</option>
      <option value="SUSPENDED">Suspended</option>
    </select>
  </div>

  <div class="card overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
        <tr>
          <th class="px-4 py-3">Tenant</th>
          <th class="px-4 py-3">Plan</th>
          <th class="px-4 py-3">Status</th>
          <th class="px-4 py-3 text-right">MRR</th>
          <th class="px-4 py-3">Branches</th>
          <th class="px-4 py-3">Users</th>
          <th class="px-4 py-3 text-right">Actions</th>
        </tr>
      </thead>
      <tbody>
        <template x-for="t in tenants" :key="t.id">
          <tr class="border-t hover:bg-gray-50">
            <td class="px-4 py-3">
              <div class="font-medium" x-text="t.name"></div>
              <div class="text-xs text-gray-500" x-text="t.code + ' · ' + t.contact_email"></div>
            </td>
            <td class="px-4 py-3" x-text="t.plan || '-'"></td>
            <td class="px-4 py-3">
              <span class="px-2 py-0.5 rounded-full text-xs"
                    :class="{
                      'bg-green-100 text-green-700': t.subscription_status === 'ACTIVE',
                      'bg-yellow-100 text-yellow-700': t.subscription_status === 'TRIAL',
                      'bg-red-100 text-red-700': t.subscription_status === 'SUSPENDED'
                    }" x-text="t.subscription_status"></span>
            </td>
            <td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(t.monthly_price)"></td>
            <td class="px-4 py-3 text-center" x-text="t.branches_count"></td>
            <td class="px-4 py-3 text-center" x-text="t.users_count"></td>
            <td class="px-4 py-3 text-right">
              <button x-show="t.is_active && t.subscription_status !== 'SUSPENDED'"
                      @click="suspend(t)" class="text-xs text-red-600 mr-2">Suspend</button>
              <button x-show="!t.is_active || t.subscription_status === 'SUSPENDED'"
                      @click="activate(t)" class="text-xs text-green-600">Activate</button>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <div x-show="tenants.length === 0" class="p-8 text-center text-gray-400">No tenants</div>
  </div>
</div>
<script>
function tenantsPage() {
  return {
    tenants: [], search: '', filter: '',
    async load() {
      const q = new URLSearchParams({ search: this.search, status: this.filter }).toString();
      this.tenants = await apiFetch(`/saas/admin/tenants/?${q}`);
    },
    async suspend(t) {
      if (!confirm(`Suspend ${t.name}?`)) return;
      await apiFetch(`/saas/admin/tenants/${t.id}/suspend/`, { method: 'POST' });
      await this.load();
    },
    async activate(t) {
      await apiFetch(`/saas/admin/tenants/${t.id}/activate/`, { method: 'POST' });
      await this.load();
    }
  }
}
</script>
{% endblock %}
'''


ADMIN_PLANS = '''
{% extends "pos/admin/base.html" %}
{% block title %}Plans{% endblock %}
{% block content %}
<div class="p-6" x-data="plansPage()" x-init="load()">
  <div class="flex justify-between items-center mb-6">
    <h1 class="text-2xl font-bold">Subscription Plans</h1>
    <button @click="showModal = true; form = empty()" class="btn-primary">+ Add Plan</button>
  </div>
  <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
    <template x-for="p in plans" :key="p.code">
      <div class="card p-5">
        <div class="text-xs text-gray-500 uppercase" x-text="p.code"></div>
        <div class="font-bold text-lg" x-text="p.name"></div>
        <div class="text-2xl font-bold text-indigo-600 mt-2" x-text="formatCurrency(p.monthly_price_zmw)"></div>
        <div class="text-xs text-gray-500 mb-3">per month</div>
        <div class="space-y-1 text-xs border-t pt-3">
          <div><span x-text="p.max_branches"></span> branches</div>
          <div><span x-text="p.max_users"></span> users</div>
        </div>
        <button @click="edit(p)" class="mt-3 text-xs text-indigo-600 hover:underline">Edit</button>
      </div>
    </template>
  </div>

  <template x-if="showModal">
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-lg w-full p-6">
        <h2 class="text-xl font-bold mb-4" x-text="form.id ? 'Edit Plan' : 'New Plan'"></h2>
        <form @submit.prevent="save()" class="space-y-3">
          <div class="grid grid-cols-2 gap-3">
            <input placeholder="Code" x-model="form.code" class="input-field" required :disabled="!!form.id">
            <input placeholder="Name" x-model="form.name" class="input-field" required>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <input type="number" step="0.01" placeholder="Monthly (ZMW)" x-model="form.monthly_price_zmw" class="input-field">
            <input type="number" step="0.01" placeholder="Yearly (ZMW)" x-model="form.yearly_price_zmw" class="input-field">
          </div>
          <div class="grid grid-cols-3 gap-2">
            <input type="number" placeholder="Max branches" x-model="form.max_branches" class="input-field">
            <input type="number" placeholder="Max users" x-model="form.max_users" class="input-field">
            <input type="number" placeholder="Trial days" x-model="form.trial_days" class="input-field">
          </div>
          <button type="submit" class="btn-primary w-full">Save</button>
        </form>
      </div>
    </div>
  </template>
</div>
<script>
function plansPage() {
  return {
    plans: [], showModal: false,
    form: { code:'', name:'', monthly_price_zmw:0, yearly_price_zmw:0,
            max_branches:1, max_users:3, max_devices:2, trial_days:0 },
    empty() {
      return { code:'', name:'', monthly_price_zmw:0, yearly_price_zmw:0,
               max_branches:1, max_users:3, max_devices:2, trial_days:0 };
    },
    async load() { this.plans = await apiFetch('/saas/admin/plans/'); },
    edit(p) { this.form = { ...p }; this.showModal = true; },
    async save() {
      try {
        await apiFetch('/saas/admin/plans/', { method: 'POST', body: JSON.stringify(this.form) });
        this.showModal = false;
        await this.load();
      } catch (e) { alert(e.response?.data?.error || 'Failed'); }
    }
  }
}
</script>
{% endblock %}
'''


ADMIN_BILLING = '''
{% extends "pos/admin/base.html" %}
{% block title %}Billing{% endblock %}
{% block content %}
<div class="p-6" x-data="billingPage()" x-init="load()">
  <div class="flex justify-between items-center mb-6">
    <h1 class="text-2xl font-bold">Billing</h1>
    <button @click="showInvModal = true" class="btn-primary">+ New Invoice</button>
  </div>

  <div class="flex gap-2 mb-4 border-b">
    <template x-for="t in ['invoices','payments']" :key="t">
      <button @click="tab = t"
              :class="tab === t ? 'border-b-2 border-indigo-600 text-indigo-600' : 'text-gray-500'"
              class="px-4 py-2 text-sm font-medium capitalize" x-text="t"></button>
    </template>
  </div>

  <div x-show="tab === 'invoices'" class="card overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
        <tr>
          <th class="px-4 py-3">Invoice #</th>
          <th class="px-4 py-3">Tenant</th>
          <th class="px-4 py-3">Date</th>
          <th class="px-4 py-3 text-right">Total</th>
          <th class="px-4 py-3 text-right">Balance</th>
          <th class="px-4 py-3">Status</th>
        </tr>
      </thead>
      <tbody>
        <template x-for="i in invoices" :key="i.id">
          <tr class="border-t">
            <td class="px-4 py-3 font-mono text-xs" x-text="i.invoice_number"></td>
            <td class="px-4 py-3" x-text="i.tenant_name"></td>
            <td class="px-4 py-3 text-gray-500" x-text="i.invoice_date"></td>
            <td class="px-4 py-3 text-right" x-text="formatCurrency(i.total)"></td>
            <td class="px-4 py-3 text-right font-semibold" x-text="formatCurrency(i.balance_due)"></td>
            <td class="px-4 py-3">
              <span class="text-xs px-2 py-0.5 rounded-full"
                    :class="{
                      'bg-green-100 text-green-700': i.status === 'PAID',
                      'bg-blue-100 text-blue-700': i.status === 'SENT',
                      'bg-red-100 text-red-700': i.status === 'OVERDUE',
                      'bg-gray-200': i.status === 'VOID'
                    }" x-text="i.status"></span>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <div x-show="invoices.length === 0" class="p-8 text-center text-gray-400">No invoices</div>
  </div>

  <div x-show="tab === 'payments'" class="card overflow-hidden">
    <table class="w-full text-sm">
      <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
        <tr>
          <th class="px-4 py-3">Payment #</th>
          <th class="px-4 py-3">Tenant</th>
          <th class="px-4 py-3">Date</th>
          <th class="px-4 py-3">Method</th>
          <th class="px-4 py-3 text-right">Amount</th>
        </tr>
      </thead>
      <tbody>
        <template x-for="p in payments" :key="p.id">
          <tr class="border-t">
            <td class="px-4 py-3 font-mono text-xs" x-text="p.payment_number"></td>
            <td class="px-4 py-3" x-text="p.tenant_name"></td>
            <td class="px-4 py-3 text-gray-500" x-text="p.payment_date"></td>
            <td class="px-4 py-3" x-text="p.payment_method"></td>
            <td class="px-4 py-3 text-right font-semibold text-green-700" x-text="formatCurrency(p.amount)"></td>
          </tr>
        </template>
      </tbody>
    </table>
    <div x-show="payments.length === 0" class="p-8 text-center text-gray-400">No payments</div>
  </div>

  <template x-if="showInvModal">
    <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-md w-full p-6">
        <h2 class="text-xl font-bold mb-4">New Invoice</h2>
        <form @submit.prevent="createInvoice()" class="space-y-3">
          <select x-model="invForm.tenant_id" class="input-field" required>
            <option value="">Select tenant...</option>
            <template x-for="t in tenants" :key="t.id">
              <option :value="t.id" x-text="t.name + ' · ' + t.plan"></option>
            </template>
          </select>
          <input type="number" step="0.01" placeholder="Total" x-model="invForm.total" class="input-field" required>
          <input placeholder="Description" x-model="invForm.description" class="input-field">
          <button type="submit" class="btn-primary w-full">Create Invoice</button>
        </form>
      </div>
    </div>
  </template>
</div>
<script>
function billingPage() {
  return {
    tab: 'invoices', invoices: [], payments: [], tenants: [],
    showInvModal: false,
    invForm: { tenant_id: '', total: 0, description: '' },
    async load() {
      [this.invoices, this.payments, this.tenants] = await Promise.all([
        apiFetch('/saas/admin/invoices/'),
        apiFetch('/saas/admin/payments/'),
        apiFetch('/saas/admin/tenants/'),
      ]);
    },
    async createInvoice() {
      try {
        await apiFetch('/saas/admin/invoices/', {
          method: 'POST',
          body: JSON.stringify(this.invForm),
        });
        this.showInvModal = false;
        this.invForm = { tenant_id: '', total: 0, description: '' };
        await this.load();
      } catch (e) { alert(e.response?.data?.error || 'Failed'); }
    }
  }
}
</script>
{% endblock %}
'''


def main():
    print("=" * 60)
    print("  POS FRONTEND — Django-Served (No Node)")
    print("=" * 60)
    print()

    if not BACKEND_PATH.exists():
        print(f"[ERROR] Backend not found: {BACKEND_PATH}")
        sys.exit(1)

    os.chdir(BACKEND_PATH)
    python = get_python()

    # Step 1: Views
    print("[1/6] Creating views_web.py...")
    write_file(BACKEND_PATH / "core" / "views_web.py", VIEWS_WEB)
    print()

    # Step 2: URLs
    print("[2/6] Creating urls_web.py...")
    write_file(BACKEND_PATH / "core" / "urls_web.py", URLS_WEB)

    print("[3/6] Patching main urls.py...")
    main_urls = BACKEND_PATH / "pos_backend" / "urls.py"
    with open(main_urls, "r", encoding="utf-8") as f:
        content = f.read()
    if "urls_web" not in content:
        content = content.replace(
            "urlpatterns = [\n",
            "urlpatterns = [\n    path('', include('core.urls_web')),\n",
        )
        with open(main_urls, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
        print("  [PATCH] pos_backend/urls.py")
    print()

    # Step 3: Static
    print("[4/6] Creating static JS...")
    write_file(BACKEND_PATH / "static" / "pos" / "api.js", API_JS)
    write_file(BACKEND_PATH / "static" / "pos" / "barcode.js", BARCODE_JS)
    print()

    # Step 4: Templates
    print("[5/6] Creating templates...")
    tpl = BACKEND_PATH / "templates" / "pos"

    write_file(tpl / "base.html", BASE_TEMPLATE)
    write_file(tpl / "_nav.html", NAV_TEMPLATE)
    write_file(tpl / "login.html", LOGIN_HTML)
    write_file(tpl / "branch_select.html", BRANCH_SELECT_HTML)
    write_file(tpl / "pos.html", POS_HTML)
    write_file(tpl / "dashboard.html", DASHBOARD_HTML)
    write_file(tpl / "products.html", PRODUCTS_HTML)
    write_file(tpl / "invoices.html", INVOICES_HTML)
    write_file(tpl / "reports.html", REPORTS_HTML)
    write_file(tpl / "settings.html", SETTINGS_HTML)

    write_file(tpl / "admin" / "base.html", ADMIN_BASE)
    write_file(tpl / "admin" / "dashboard.html", ADMIN_DASHBOARD)
    write_file(tpl / "admin" / "applications.html", ADMIN_APPLICATIONS)
    write_file(tpl / "admin" / "tenants.html", ADMIN_TENANTS)
    write_file(tpl / "admin" / "plans.html", ADMIN_PLANS)
    write_file(tpl / "admin" / "billing.html", ADMIN_BILLING)
    print()

    # Step 5: Clean failed npm attempt
    print("[6/6] Cleaning up failed React attempt...")
    frontend_dir = BACKEND_PATH / "frontend"
    if frontend_dir.exists():
        import shutil
        shutil.rmtree(frontend_dir)
        print("  [DELETE] frontend/ (React)")
    print()

    # Verify
    print("Verifying...")
    subprocess.run([str(python), "manage.py", "check"], cwd=BACKEND_PATH, check=False)
    print()

    print("=" * 60)
    print("  ✅ FRONTEND READY (Django-served)")
    print("=" * 60)
    print()
    print("START THE SERVER:")
    print(f"  cd {BACKEND_PATH}")
    print("  .\\venv\\Scripts\\Activate.ps1")
    print("  python manage.py runserver")
    print()
    print("OPEN IN BROWSER:")
    print("  http://localhost:8000/")
    print()
    print("LOGIN:")
    print("  Owner:          demo_owner / Demo@123456")
    print("  Platform admin: admin / Admin@123456")
    print()
    print("ALL PAGES:")
    print("  /login")
    print("  /select-branch")
    print("  /pos")
    print("  /dashboard")
    print("  /products")
    print("  /invoices")
    print("  /reports")
    print("  /settings")
    print("  /admin  (platform admin only)")
    print("  /admin/applications, /admin/tenants, /admin/plans, /admin/billing")
    print()
    print("NO NODE. NO BUILD. NO NPM.")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()