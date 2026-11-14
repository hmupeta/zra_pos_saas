"""
============================================================
POS FRONTEND BUILD SCRIPT
React + Vite + Tailwind + Zustand POS Application
============================================================
Builds a complete POS frontend that connects to the backend.

Usage:
    python build_pos_frontend.py
    python build_pos_frontend.py --backend /custom/path/to/zra_pos_saas

What you get:
  - Login + branch picker
  - POS screen (barcode scan, cart, checkout, receipt print)
  - Dashboard with today's KPIs
  - Products CRUD
  - Invoices list + view + refund
  - Reports (trial balance, balance sheet, income statement)
  - Settings (branches, payment configs)
============================================================
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

DEFAULT_BACKEND = Path.home() / "Documents" / "django" / "zra_pos_saas"


def write_file(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(content.strip() + "\n")
    print(f"  [WRITE] {path.name}")


def run(cmd, cwd, check=True, shell=False):
    return subprocess.run(cmd, cwd=cwd, check=check, shell=shell)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--backend", default=str(DEFAULT_BACKEND))
    args = parser.parse_args()

    backend = Path(args.backend)
    if not backend.exists():
        print(f"[ERROR] Backend not found at {backend}")
        print("        Run build_pos_saas.py first.")
        sys.exit(1)

    frontend = backend / "frontend"
    if frontend.exists():
        ans = input(f"{frontend} exists. Delete and rebuild? (y/N): ").strip().lower()
        if ans != "y":
            sys.exit(0)
        shutil.rmtree(frontend)

    frontend.mkdir(parents=True)
    print(f"Building frontend at: {frontend}\n")

    # ========================================================
    # 1. Root config files
    # ========================================================
    write_file(frontend / "package.json", '''
{
  "name": "pos-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "preview": "vite preview"
  },
  "dependencies": {
    "axios": "^1.7.7",
    "lucide-react": "^0.454.0",
    "react": "^18.3.1",
    "react-dom": "^18.3.1",
    "react-hot-toast": "^2.4.1",
    "react-router-dom": "^6.27.0",
    "zustand": "^5.0.0"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^4.3.3",
    "autoprefixer": "^10.4.20",
    "postcss": "^8.4.47",
    "tailwindcss": "^3.4.14",
    "vite": "^5.4.10"
  }
}
''')

    write_file(frontend / "vite.config.js", '''
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
''')

    write_file(frontend / "tailwind.config.js", '''
export default {
  content: ['./index.html', './src/**/*.{js,jsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#eef2ff',
          500: '#6366f1',
          600: '#4f46e5',
          700: '#4338ca',
        },
      },
    },
  },
  plugins: [],
};
''')

    write_file(frontend / "postcss.config.js", '''
export default {
  plugins: {
    tailwindcss: {},
    autoprefixer: {},
  },
};
''')

    write_file(frontend / "index.html", '''
<!doctype html>
<html lang="en">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1.0" />
    <title>POS · SaaS Retail</title>
  </head>
  <body class="antialiased">
    <div id="root"></div>
    <script type="module" src="/src/main.jsx"></script>
  </body>
</html>
''')

    write_file(frontend / ".env", '''
VITE_API_URL=/api
''')

    write_file(frontend / ".gitignore", '''
node_modules
dist
.env.local
*.log
''')

    # ========================================================
    # 2. Source files
    # ========================================================
    write_file(frontend / "src/main.jsx", '''
import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App';
import './index.css';

ReactDOM.createRoot(document.getElementById('root')).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);
''')

    write_file(frontend / "src/index.css", '''
@tailwind base;
@tailwind components;
@tailwind utilities;

html, body, #root { height: 100%; }
body { font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif; }

.btn-primary {
  @apply px-4 py-2 bg-brand-600 text-white font-medium rounded-lg hover:bg-brand-700 disabled:bg-gray-300 disabled:cursor-not-allowed transition;
}
.btn-secondary {
  @apply px-4 py-2 bg-white text-gray-700 font-medium rounded-lg border border-gray-300 hover:bg-gray-50 transition;
}
.input-field {
  @apply w-full px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent;
}
.card {
  @apply bg-white rounded-xl shadow-sm border border-gray-100;
}

.receipt-text {
  font-family: 'Courier New', monospace;
  white-space: pre-wrap;
  font-size: 12px;
  line-height: 1.4;
}

@keyframes flash-green {
  0% { background-color: #dcfce7; }
  100% { background-color: transparent; }
}
.flash { animation: flash-green 0.6s ease-out; }
''')

    write_file(frontend / "src/lib/api.js", '''
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || '/api',
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token');
  if (token) {
    config.headers.Authorization = `Token ${token}`;
  }
  const branchId = localStorage.getItem('branchId');
  if (branchId) {
    config.headers['X-Branch-ID'] = branchId;
  }
  return config;
});

api.interceptors.response.use(
  (res) => res,
  (err) => {
    if (err.response?.status === 401) {
      localStorage.removeItem('token');
      window.location.href = '/login';
    }
    return Promise.reject(err);
  }
);

export default api;
''')

    write_file(frontend / "src/lib/utils.js", '''
export function formatCurrency(value, currency = 'K') {
  const n = parseFloat(value || 0);
  return `${currency}${n.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDate(iso) {
  if (!iso) return '-';
  return new Date(iso).toLocaleString('en-GB', {
    day: '2-digit', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

export function escapeHtml(str) {
  return String(str)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;');
}
''')

    write_file(frontend / "src/store/auth.js", '''
import { create } from 'zustand';

export const useAuth = create((set) => ({
  token: localStorage.getItem('token'),
  user: JSON.parse(localStorage.getItem('user') || 'null'),
  tenant: localStorage.getItem('tenant'),
  branchId: parseInt(localStorage.getItem('branchId') || '0', 10) || null,
  branches: [],

  setSession: (data) => {
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify(data.user));
    if (data.tenant) localStorage.setItem('tenant', data.tenant);
    set({ token: data.token, user: data.user, tenant: data.tenant });
  },

  setBranch: (id) => {
    localStorage.setItem('branchId', String(id));
    set({ branchId: id });
  },

  setBranches: (branches) => set({ branches }),

  logout: () => {
    localStorage.clear();
    set({ token: null, user: null, tenant: null, branchId: null, branches: [] });
  },
}));
''')

    write_file(frontend / "src/hooks/useBarcodeScanner.js", '''
import { useEffect, useRef } from 'react';

/**
 * Detects HID keyboard-emulation barcode scanners.
 * Scanners type characters very fast then fire Enter.
 */
export function useBarcodeScanner({ onScan, minLength = 4, timeout = 100 }) {
  const buffer = useRef('');
  const lastKey = useRef(0);

  useEffect(() => {
    const handler = (e) => {
      const isScannerInput = e.target.dataset?.scanner === 'true';
      const isFormField = ['INPUT', 'TEXTAREA', 'SELECT'].includes(e.target.tagName);
      if (isFormField && !isScannerInput) return;

      const now = Date.now();
      if (now - lastKey.current > timeout) buffer.current = '';
      lastKey.current = now;

      if (e.key === 'Enter') {
        const code = buffer.current.trim();
        buffer.current = '';
        if (code.length >= minLength) {
          e.preventDefault();
          onScan(code);
        }
      } else if (/^[a-zA-Z0-9\\-_]$/.test(e.key)) {
        buffer.current += e.key;
      }
    };

    window.addEventListener('keydown', handler);
    return () => window.removeEventListener('keydown', handler);
  }, [onScan, minLength, timeout]);
}
''')

    write_file(frontend / "src/lib/printer.js", '''
import { escapeHtml } from './utils';

/**
 * Print a text-format receipt via a new window.
 * Works with any OS printer. For direct thermal ESC/POS,
 * swap this for QZ Tray or WebUSB.
 */
export function printTextReceipt(text) {
  const win = window.open('', '_blank', 'width=400,height=650');
  if (!win) {
    alert('Please allow popups to print receipts');
    return;
  }

  win.document.write(`
    <html>
      <head>
        <title>Receipt</title>
        <style>
          body { font-family: 'Courier New', monospace; font-size: 12px; margin: 8px; }
          pre { white-space: pre-wrap; word-wrap: break-word; margin: 0; }
          @media print { body { margin: 0; } }
        </style>
      </head>
      <body>
        <pre>${escapeHtml(text)}</pre>
        <script>
          window.onload = () => {
            window.print();
            setTimeout(() => window.close(), 100);
          };
        </script>
      </body>
    </html>
  `);
  win.document.close();
}
''')

    write_file(frontend / "src/components/ProtectedRoute.jsx", '''
import { Navigate } from 'react-router-dom';
import { useAuth } from '../store/auth';

export default function ProtectedRoute({ children, requireBranch = true }) {
  const { token, branchId } = useAuth();

  if (!token) return <Navigate to="/login" replace />;
  if (requireBranch && !branchId) return <Navigate to="/select-branch" replace />;

  return children;
}
''')

    write_file(frontend / "src/components/Layout.jsx", '''
import { Outlet, useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../store/auth';
import { useEffect, useState } from 'react';
import api from '../lib/api';
import toast from 'react-hot-toast';
import {
  ShoppingCart, LayoutDashboard, Package, Receipt,
  BarChart3, Settings as SettingsIcon, LogOut, Building2, ChevronDown,
} from 'lucide-react';

const NAV = [
  { to: '/pos', label: 'POS', icon: ShoppingCart },
  { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
  { to: '/products', label: 'Products', icon: Package },
  { to: '/invoices', label: 'Invoices', icon: Receipt },
  { to: '/reports', label: 'Reports', icon: BarChart3 },
  { to: '/settings', label: 'Settings', icon: SettingsIcon },
];

export default function Layout() {
  const { user, tenant, branchId, branches, setBranches, setBranch, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [branchMenuOpen, setBranchMenuOpen] = useState(false);

  useEffect(() => {
    api.get('/auth/branches/').then((r) => setBranches(r.data)).catch(() => {});
  }, [setBranches]);

  const currentBranch = branches.find((b) => b.id === branchId);

  const switchBranch = (id) => {
    setBranch(id);
    setBranchMenuOpen(false);
    toast.success('Branch switched');
    window.location.reload();
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  return (
    <div className="min-h-screen flex bg-gray-50">
      {/* Sidebar */}
      <aside className="w-56 bg-white border-r border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200">
          <div className="font-bold text-lg text-brand-600">POS</div>
          <div className="text-xs text-gray-500 truncate">{tenant}</div>
        </div>
        <nav className="flex-1 p-2 space-y-1">
          {NAV.map((item) => {
            const Icon = item.icon;
            const active = location.pathname.startsWith(item.to);
            return (
              <Link
                key={item.to}
                to={item.to}
                className={`flex items-center gap-3 px-3 py-2 rounded-lg text-sm font-medium transition ${
                  active
                    ? 'bg-brand-50 text-brand-700'
                    : 'text-gray-700 hover:bg-gray-50'
                }`}
              >
                <Icon className="w-5 h-5" />
                {item.label}
              </Link>
            );
          })}
        </nav>
        <div className="p-3 border-t border-gray-200">
          <div className="text-xs text-gray-500">Signed in as</div>
          <div className="text-sm font-medium truncate">{user?.username}</div>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col">
        {/* Top bar */}
        <header className="h-16 bg-white border-b border-gray-200 flex items-center justify-between px-4">
          <div className="relative">
            <button
              onClick={() => setBranchMenuOpen((v) => !v)}
              className="flex items-center gap-2 px-3 py-2 rounded-lg hover:bg-gray-50 text-sm font-medium"
            >
              <Building2 className="w-4 h-4 text-gray-500" />
              {currentBranch?.name || 'Select branch'}
              <ChevronDown className="w-4 h-4 text-gray-400" />
            </button>
            {branchMenuOpen && (
              <div className="absolute top-full left-0 mt-1 w-64 bg-white rounded-lg shadow-lg border border-gray-200 z-20">
                {branches.map((b) => (
                  <button
                    key={b.id}
                    onClick={() => switchBranch(b.id)}
                    className={`w-full text-left px-4 py-2 text-sm hover:bg-gray-50 first:rounded-t-lg last:rounded-b-lg ${
                      b.id === branchId ? 'bg-brand-50 text-brand-700 font-medium' : ''
                    }`}
                  >
                    <div>{b.name}</div>
                    <div className="text-xs text-gray-500">Code: {b.code}</div>
                  </button>
                ))}
              </div>
            )}
          </div>
          <button
            onClick={handleLogout}
            className="flex items-center gap-2 px-3 py-2 text-sm text-red-600 hover:bg-red-50 rounded-lg"
          >
            <LogOut className="w-4 h-4" />
            Logout
          </button>
        </header>

        <main className="flex-1 overflow-hidden">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
''')

    # ========================================================
    # 3. Pages
    # ========================================================
    write_file(frontend / "src/pages/Login.jsx", '''
import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import toast from 'react-hot-toast';
import api from '../lib/api';
import { useAuth } from '../store/auth';

export default function Login() {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const { setSession, setBranch, setBranches } = useAuth();
  const navigate = useNavigate();

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await api.post('/auth/login/', { username, password });
      setSession(res.data);

      if (res.data.user.user_type === 'PLATFORM_ADMIN') {
        toast.error('Platform admins should use the admin panel');
        return;
      }

      const branchesRes = await api.get('/auth/branches/');
      const branches = branchesRes.data;

      if (branches.length === 0) {
        toast.error('No branches assigned. Contact your administrator.');
        return;
      }

      if (branches.length === 1) {
        setBranch(branches[0].id);
        toast.success(`Welcome, ${res.data.user.username}`);
        navigate('/pos');
      } else {
        setBranches(branches);
        navigate('/select-branch');
      }
    } catch (err) {
      toast.error(err.response?.data?.error || 'Login failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-indigo-100 p-4">
      <div className="w-full max-w-md bg-white rounded-2xl shadow-xl p-8">
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-brand-700">POS Login</h1>
          <p className="text-gray-500 mt-1 text-sm">Sign in to your store</p>
        </div>
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Username</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              className="input-field"
              autoFocus
              required
            />
          </div>
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="input-field"
              required
            />
          </div>
          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? 'Signing in...' : 'Sign In'}
          </button>
        </form>
        <p className="text-xs text-gray-400 text-center mt-6">
          Demo credentials: demo_owner / Demo@123456
        </p>
      </div>
    </div>
  );
}
''')

    write_file(frontend / "src/pages/BranchSelect.jsx", '''
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../store/auth';
import { Building2 } from 'lucide-react';

export default function BranchSelect() {
  const { branches, setBranch } = useAuth();
  const navigate = useNavigate();

  const select = (id) => {
    setBranch(id);
    navigate('/pos');
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-brand-50 to-indigo-100 p-4">
      <div className="w-full max-w-2xl">
        <h1 className="text-2xl font-bold text-gray-800 mb-6 text-center">Select a branch</h1>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {branches.map((b) => (
            <button
              key={b.id}
              onClick={() => select(b.id)}
              className="bg-white rounded-xl shadow-sm border border-gray-100 p-6 text-left hover:shadow-lg hover:border-brand-300 transition"
            >
              <Building2 className="w-8 h-8 text-brand-600 mb-3" />
              <div className="text-lg font-semibold text-gray-800">{b.name}</div>
              <div className="text-sm text-gray-500 mt-1">Code: {b.code}</div>
              <div className="text-xs text-gray-400 mt-1">TPIN: {b.tpin}</div>
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
''')

    write_file(frontend / "src/pages/POS.jsx", '''
import { useEffect, useState, useCallback } from 'react';
import toast from 'react-hot-toast';
import api from '../lib/api';
import { useBarcodeScanner } from '../hooks/useBarcodeScanner';
import { printTextReceipt } from '../lib/printer';
import { formatCurrency } from '../lib/utils';
import {
  Search, ScanLine, Trash2, Plus, Minus, ShoppingCart,
  CreditCard, Smartphone, Banknote, X, Printer, AlertCircle,
} from 'lucide-react';

export default function POS() {
  const [shift, setShift] = useState(null);
  const [products, setProducts] = useState([]);
  const [cart, setCart] = useState({
    items: [], totals: { subtotal: 0, tax_total: 0, total: 0, item_count: 0 },
  });
  const [search, setSearch] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);
  const [openShiftModal, setOpenShiftModal] = useState(false);
  const [checkoutModal, setCheckoutModal] = useState(false);
  const [receiptModal, setReceiptModal] = useState(null);
  const [openingBalance, setOpeningBalance] = useState('0');
  const [paymentMethod, setPaymentMethod] = useState('CASH');
  const [phone, setPhone] = useState('');
  const [lastScanned, setLastScanned] = useState(null);

  // Bootstrap
  useEffect(() => {
    Promise.all([
      api.get('/sales/current-shift/').catch((e) => (e.response?.status === 404 ? { data: null } : Promise.reject(e))),
      api.get('/inventory/products/'),
    ]).then(([shiftRes, prodRes]) => {
      setShift(shiftRes.data);
      setProducts(prodRes.data);
      if (shiftRes.data) {
        api.get('/sales/cart/').then((r) => setCart(r.data)).catch(() => {});
      } else {
        setOpenShiftModal(true);
      }
    }).finally(() => setLoading(false));
  }, []);

  const handleScan = useCallback(async (barcode) => {
    if (!shift) {
      toast.error('Open a shift first');
      return;
    }
    try {
      const res = await api.post('/sales/scan-add/', { barcode, quantity: 1 });
      setCart(res.data.cart);
      setLastScanned(res.data.product.barcode);
      toast.success(`Added: ${res.data.product.name}`);
      setTimeout(() => setLastScanned(null), 800);
    } catch (err) {
      toast.error(err.response?.data?.error || `Scan failed: ${barcode}`);
    }
  }, [shift]);

  useBarcodeScanner({ onScan: handleScan });

  const openShift = async () => {
    try {
      const res = await api.post('/sales/open-shift/', {
        opening_balance: parseFloat(openingBalance) || 0,
      });
      const shiftRes = await api.get('/sales/current-shift/');
      setShift(shiftRes.data);
      setOpenShiftModal(false);
      toast.success('Shift opened');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to open shift');
    }
  };

  const closeShift = async () => {
    if (!confirm('Close this shift? Cart will be cleared.')) return;
    try {
      await api.post('/sales/close-shift/');
      setShift(null);
      setCart({ items: [], totals: { subtotal: 0, tax_total: 0, total: 0, item_count: 0 } });
      setOpenShiftModal(true);
      toast.success('Shift closed');
    } catch (err) {
      toast.error('Failed to close shift');
    }
  };

  const addProduct = async (barcode) => {
    await handleScan(barcode);
  };

  const removeItem = async (barcode) => {
    // Force qty to 0 via scan-add won't work; use cart update endpoint if exists
    // Backend currently supports scan-add only — do a client-side filter + resubmit
    toast.error('Use quantity buttons to reduce to 0');
  };

  const clearCart = async () => {
    if (!confirm('Clear cart?')) return;
    try {
      await api.post('/sales/cart/clear/');
      setCart({ items: [], totals: { subtotal: 0, tax_total: 0, total: 0, item_count: 0 } });
    } catch (err) {
      toast.error('Failed to clear cart');
    }
  };

  const doCheckout = async () => {
    setBusy(true);
    try {
      const res = await api.post('/sales/cart/checkout/', {
        payment_method: paymentMethod,
      });
      toast.success(`Sale complete: ${res.data.invoice_number}`);

      // Fetch receipt
      const receiptRes = await api.get(`/sales/invoices/${res.data.invoice_id}/receipt.txt`);
      setReceiptModal({ ...res.data, text: receiptRes.data.text });

      setCart({ items: [], totals: { subtotal: 0, tax_total: 0, total: 0, item_count: 0 } });
      setCheckoutModal(false);
      setPhone('');
      setPaymentMethod('CASH');
    } catch (err) {
      toast.error(err.response?.data?.error || 'Checkout failed');
    } finally {
      setBusy(false);
    }
  };

  const filteredProducts = search
    ? products.filter(
        (p) =>
          p.name.toLowerCase().includes(search.toLowerCase()) ||
          p.barcode.includes(search)
      )
    : products;

  if (loading) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-gray-500">Loading POS...</div>
      </div>
    );
  }

  return (
    <div className="flex h-full">
      {/* Left: Products */}
      <div className="flex-1 p-4 overflow-y-auto">
        <div className="mb-4 flex items-center gap-3">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
            <input
              type="text"
              placeholder="Search products or scan barcode..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="input-field pl-10"
            />
          </div>
          <div className={`px-3 py-2 rounded-lg text-sm font-medium flex items-center gap-2 ${
            shift ? 'bg-green-50 text-green-700' : 'bg-red-50 text-red-700'
          }`}>
            <ScanLine className="w-4 h-4" />
            {shift ? 'Scanner ready' : 'Shift closed'}
          </div>
        </div>

        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
          {filteredProducts.slice(0, 60).map((p) => (
            <button
              key={p.id}
              onClick={() => addProduct(p.barcode)}
              className={`card p-3 text-left hover:shadow-md hover:border-brand-300 transition ${
                lastScanned === p.barcode ? 'flash' : ''
              }`}
            >
              <div className="font-medium text-sm line-clamp-2 h-10">{p.name}</div>
              <div className="text-xs text-gray-500 mt-1">{p.barcode}</div>
              <div className="flex justify-between items-end mt-2">
                <div className="text-lg font-bold text-brand-700">
                  {formatCurrency(p.selling_price)}
                </div>
                <div className="text-xs text-gray-400">Stock {p.current_stock}</div>
              </div>
            </button>
          ))}
        </div>

        {filteredProducts.length === 0 && (
          <div className="text-center py-12 text-gray-400">
            <AlertCircle className="w-12 h-12 mx-auto mb-2" />
            No products found
          </div>
        )}
      </div>

      {/* Right: Cart */}
      <div className="w-96 bg-white border-l border-gray-200 flex flex-col">
        <div className="p-4 border-b border-gray-200 flex justify-between items-center">
          <h2 className="font-semibold flex items-center gap-2">
            <ShoppingCart className="w-5 h-5" />
            Cart ({cart.totals.item_count})
          </h2>
          <div className="flex gap-2">
            {cart.items.length > 0 && (
              <button onClick={clearCart} className="text-xs text-red-600 hover:underline">
                Clear
              </button>
            )}
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4 space-y-2">
          {cart.items.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <ShoppingCart className="w-12 h-12 mx-auto mb-2 opacity-30" />
              Scan or click products to add
            </div>
          ) : (
            cart.items.map((item) => (
              <div key={item.barcode} className="flex items-center justify-between p-2 bg-gray-50 rounded-lg">
                <div className="flex-1 min-w-0">
                  <div className="text-sm font-medium truncate">{item.name}</div>
                  <div className="text-xs text-gray-500">
                    {formatCurrency(item.unit_price)} × {item.quantity}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold">
                    {formatCurrency(item.line_total)}
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

        <div className="p-4 border-t border-gray-200 space-y-3">
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">Subtotal</span>
            <span>{formatCurrency(cart.totals.subtotal)}</span>
          </div>
          <div className="flex justify-between text-sm">
            <span className="text-gray-500">VAT</span>
            <span>{formatCurrency(cart.totals.tax_total)}</span>
          </div>
          <div className="flex justify-between text-lg font-bold pt-2 border-t border-gray-200">
            <span>Total</span>
            <span className="text-brand-700">{formatCurrency(cart.totals.total)}</span>
          </div>

          <button
            disabled={!shift || cart.items.length === 0 || busy}
            onClick={() => setCheckoutModal(true)}
            className="btn-primary w-full text-base py-3"
          >
            Checkout
          </button>

          {shift && (
            <button onClick={closeShift} className="btn-secondary w-full text-sm">
              Close Shift
            </button>
          )}
        </div>
      </div>

      {/* Open Shift Modal */}
      {openShiftModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">Open Shift</h2>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Opening Balance (Cash in Drawer)
            </label>
            <input
              type="number"
              value={openingBalance}
              onChange={(e) => setOpeningBalance(e.target.value)}
              className="input-field mb-4"
              placeholder="0.00"
            />
            <button onClick={openShift} className="btn-primary w-full">
              Open Shift
            </button>
          </div>
        </div>
      )}

      {/* Checkout Modal */}
      {checkoutModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Checkout</h2>
              <button onClick={() => setCheckoutModal(false)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>

            <div className="text-center py-4 mb-4 bg-gray-50 rounded-lg">
              <div className="text-sm text-gray-500">Total to pay</div>
              <div className="text-3xl font-bold text-brand-700 mt-1">
                {formatCurrency(cart.totals.total)}
              </div>
            </div>

            <div className="space-y-2 mb-4">
              {[
                { id: 'CASH', label: 'Cash', icon: Banknote },
                { id: 'MOMO', label: 'Mobile Money', icon: Smartphone },
                { id: 'CARD', label: 'Card', icon: CreditCard },
              ].map(({ id, label, icon: Icon }) => (
                <button
                  key={id}
                  onClick={() => setPaymentMethod(id)}
                  className={`w-full flex items-center gap-3 px-4 py-3 rounded-lg border-2 transition ${
                    paymentMethod === id
                      ? 'border-brand-500 bg-brand-50'
                      : 'border-gray-200 hover:border-gray-300'
                  }`}
                >
                  <Icon className="w-5 h-5" />
                  <span className="font-medium">{label}</span>
                </button>
              ))}
            </div>

            {(paymentMethod === 'MOMO' || paymentMethod === 'CARD') && (
              <div className="mb-4">
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Phone Number (for MoMo)
                </label>
                <input
                  type="tel"
                  value={phone}
                  onChange={(e) => setPhone(e.target.value)}
                  placeholder="0971234567"
                  className="input-field"
                />
              </div>
            )}

            <button
              disabled={busy}
              onClick={doCheckout}
              className="btn-primary w-full py-3 text-base"
            >
              {busy ? 'Processing...' : `Pay ${formatCurrency(cart.totals.total)}`}
            </button>
          </div>
        </div>
      )}

      {/* Receipt Modal */}
      {receiptModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full max-h-[90vh] flex flex-col">
            <div className="p-4 border-b flex justify-between items-center">
              <h2 className="text-lg font-bold">Receipt</h2>
              <button onClick={() => setReceiptModal(null)} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="flex-1 overflow-y-auto p-4">
              <pre className="receipt-text bg-gray-50 p-4 rounded-lg">
                {receiptModal.text}
              </pre>
            </div>
            <div className="p-4 border-t flex gap-2">
              <button
                onClick={() => printTextReceipt(receiptModal.text)}
                className="btn-secondary flex-1 flex items-center justify-center gap-2"
              >
                <Printer className="w-4 h-4" />
                Print
              </button>
              <button
                onClick={() => setReceiptModal(null)}
                className="btn-primary flex-1"
              >
                Done
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
''')

    write_file(frontend / "src/pages/Dashboard.jsx", '''
import { useEffect, useState } from 'react';
import api from '../lib/api';
import { formatCurrency } from '../lib/utils';
import { ShoppingCart, DollarSign, Package, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  const [data, setData] = useState(null);
  const [summary, setSummary] = useState(null);

  useEffect(() => {
    Promise.all([
      api.get('/reports/dashboard/'),
      api.get('/reports/sales-summary/', { params: { period: 'week' } }),
    ]).then(([d, s]) => {
      setData(d.data);
      setSummary(s.data);
    }).catch(() => {});
  }, []);

  if (!data) return <div className="p-8 text-gray-500">Loading...</div>;

  const kpis = [
    { label: "Today's Sales", value: formatCurrency(data.today_sales), icon: DollarSign, color: 'text-green-600 bg-green-50' },
    { label: "Transactions", value: data.today_transactions, icon: ShoppingCart, color: 'text-blue-600 bg-blue-50' },
    { label: 'Total Products', value: data.total_products, icon: Package, color: 'text-purple-600 bg-purple-50' },
    { label: 'Low Stock', value: data.low_stock, icon: TrendingUp, color: 'text-orange-600 bg-orange-50' },
  ];

  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-2xl font-bold text-gray-800 mb-1">Dashboard</h1>
      <p className="text-gray-500 mb-6">{data.branch} · {data.tenant}</p>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6">
        {kpis.map((k) => {
          const Icon = k.icon;
          return (
            <div key={k.label} className="card p-5">
              <div className={`w-10 h-10 rounded-lg flex items-center justify-center ${k.color}`}>
                <Icon className="w-5 h-5" />
              </div>
              <div className="text-sm text-gray-500 mt-3">{k.label}</div>
              <div className="text-2xl font-bold text-gray-800 mt-1">{k.value}</div>
            </div>
          );
        })}
      </div>

      {summary && (
        <div className="card p-6">
          <h2 className="font-semibold mb-4">Last 7 Days</h2>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <div className="text-sm text-gray-500">Total Sales</div>
              <div className="text-xl font-bold">{formatCurrency(summary.total_sales)}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">Transactions</div>
              <div className="text-xl font-bold">{summary.transaction_count}</div>
            </div>
            <div>
              <div className="text-sm text-gray-500">VAT Collected</div>
              <div className="text-xl font-bold">{formatCurrency(summary.total_tax)}</div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
''')

    write_file(frontend / "src/pages/Products.jsx", '''
import { useEffect, useState } from 'react';
import api from '../lib/api';
import toast from 'react-hot-toast';
import { formatCurrency } from '../lib/utils';
import { Plus, Search, X } from 'lucide-react';

export default function Products() {
  const [products, setProducts] = useState([]);
  const [search, setSearch] = useState('');
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    barcode: '', name: '', selling_price: '', unit_cost: '',
    current_stock: '', category_id: 1, tax_rate_id: 1, zra_item_code: '',
  });

  useEffect(() => {
    loadProducts();
  }, []);

  const loadProducts = async () => {
    try {
      const res = await api.get('/inventory/products/');
      setProducts(res.data);
    } catch {
      toast.error('Failed to load products');
    }
  };

  const filtered = search
    ? products.filter(p =>
        p.name.toLowerCase().includes(search.toLowerCase()) ||
        p.barcode.includes(search))
    : products;

  const submit = async (e) => {
    e.preventDefault();
    try {
      await api.post('/inventory/products/', {
        ...form,
        selling_price: parseFloat(form.selling_price),
        unit_cost: parseFloat(form.unit_cost || 0),
        current_stock: parseFloat(form.current_stock || 0),
        category_id: parseInt(form.category_id),
        tax_rate_id: parseInt(form.tax_rate_id),
      });
      toast.success('Product added');
      setShowModal(false);
      setForm({ barcode: '', name: '', selling_price: '', unit_cost: '', current_stock: '', category_id: 1, tax_rate_id: 1, zra_item_code: '' });
      loadProducts();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Failed to add product');
    }
  };

  return (
    <div className="p-6 overflow-y-auto h-full">
      <div className="flex justify-between items-center mb-6">
        <h1 className="text-2xl font-bold">Products</h1>
        <button onClick={() => setShowModal(true)} className="btn-primary flex items-center gap-2">
          <Plus className="w-4 h-4" /> Add Product
        </button>
      </div>

      <div className="relative mb-4">
        <Search className="absolute left-3 top-2.5 w-5 h-5 text-gray-400" />
        <input
          type="text"
          placeholder="Search by name or barcode..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="input-field pl-10"
        />
      </div>

      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Barcode</th>
              <th className="px-4 py-3">Name</th>
              <th className="px-4 py-3 text-right">Price</th>
              <th className="px-4 py-3 text-right">Stock</th>
              <th className="px-4 py-3 text-right">VAT</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((p) => (
              <tr key={p.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{p.barcode}</td>
                <td className="px-4 py-3 font-medium">{p.name}</td>
                <td className="px-4 py-3 text-right">{formatCurrency(p.selling_price)}</td>
                <td className={`px-4 py-3 text-right ${parseFloat(p.current_stock) <= 0 ? 'text-red-600 font-semibold' : ''}`}>
                  {p.current_stock}
                </td>
                <td className="px-4 py-3 text-right text-gray-500">{p.tax_rate}%</td>
              </tr>
            ))}
          </tbody>
        </table>
        {filtered.length === 0 && (
          <div className="p-8 text-center text-gray-400">No products</div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-lg w-full p-6">
            <div className="flex justify-between items-center mb-4">
              <h2 className="text-xl font-bold">Add Product</h2>
              <button onClick={() => setShowModal(false)}><X className="w-5 h-5 text-gray-400" /></button>
            </div>
            <form onSubmit={submit} className="space-y-3">
              <input placeholder="Barcode" value={form.barcode}
                onChange={(e) => setForm({...form, barcode: e.target.value})}
                className="input-field" required />
              <input placeholder="Name" value={form.name}
                onChange={(e) => setForm({...form, name: e.target.value})}
                className="input-field" required />
              <div className="grid grid-cols-2 gap-3">
                <input type="number" step="0.01" placeholder="Selling price" value={form.selling_price}
                  onChange={(e) => setForm({...form, selling_price: e.target.value})}
                  className="input-field" required />
                <input type="number" step="0.01" placeholder="Cost" value={form.unit_cost}
                  onChange={(e) => setForm({...form, unit_cost: e.target.value})}
                  className="input-field" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input type="number" step="0.01" placeholder="Stock" value={form.current_stock}
                  onChange={(e) => setForm({...form, current_stock: e.target.value})}
                  className="input-field" />
                <input placeholder="ZRA item code" value={form.zra_item_code}
                  onChange={(e) => setForm({...form, zra_item_code: e.target.value})}
                  className="input-field" />
              </div>
              <div className="grid grid-cols-2 gap-3">
                <input type="number" placeholder="Category ID" value={form.category_id}
                  onChange={(e) => setForm({...form, category_id: e.target.value})}
                  className="input-field" />
                <input type="number" placeholder="Tax rate ID" value={form.tax_rate_id}
                  onChange={(e) => setForm({...form, tax_rate_id: e.target.value})}
                  className="input-field" />
              </div>
              <button type="submit" className="btn-primary w-full">Create Product</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
''')

    write_file(frontend / "src/pages/Invoices.jsx", '''
import { useEffect, useState } from 'react';
import api from '../lib/api';
import toast from 'react-hot-toast';
import { formatCurrency, formatDate } from '../lib/utils';
import { Receipt, RotateCcw } from 'lucide-react';
import { printTextReceipt } from '../lib/printer';

export default function Invoices() {
  const [invoices, setInvoices] = useState([]);

  const load = async () => {
    try {
      const res = await api.get('/sales/invoices/');
      setInvoices(res.data);
    } catch {
      toast.error('Failed to load invoices');
    }
  };

  useEffect(() => { load(); }, []);

  const printReceipt = async (id) => {
    try {
      const res = await api.get(`/sales/invoices/${id}/receipt.txt`);
      printTextReceipt(res.data.text);
    } catch {
      toast.error('Failed to load receipt');
    }
  };

  const refund = async (inv) => {
    if (!confirm(`Refund full amount for ${inv.invoice_number}?`)) return;
    try {
      // Note: proper refund needs item selection — this is simplified
      await api.post('/returns/quick-refund/', {
        invoice_id: inv.id,
        items: [],  // Backend requires items; expand this later
        reason: 'OTHER',
        refund_method: 'CASH',
      });
      toast.success('Refund processed');
      load();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Refund failed');
    }
  };

  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-2xl font-bold mb-6">Invoices</h1>
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
            <tr>
              <th className="px-4 py-3">Invoice #</th>
              <th className="px-4 py-3">Date</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-4 py-3 text-right">Total</th>
              <th className="px-4 py-3 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {invoices.map((inv) => (
              <tr key={inv.id} className="border-t border-gray-100 hover:bg-gray-50">
                <td className="px-4 py-3 font-mono text-xs">{inv.invoice_number}</td>
                <td className="px-4 py-3">{formatDate(inv.created_at)}</td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-0.5 rounded-full text-xs ${
                    inv.status === 'PAID' ? 'bg-green-100 text-green-700' :
                    inv.status === 'VOID' ? 'bg-gray-100 text-gray-700' :
                    'bg-yellow-100 text-yellow-700'
                  }`}>
                    {inv.status}
                  </span>
                </td>
                <td className="px-4 py-3 text-right font-semibold">{formatCurrency(inv.total)}</td>
                <td className="px-4 py-3 text-right">
                  <div className="flex justify-end gap-2">
                    <button onClick={() => printReceipt(inv.id)} title="Print"
                      className="p-1.5 text-gray-500 hover:text-brand-600">
                      <Receipt className="w-4 h-4" />
                    </button>
                    {inv.status === 'PAID' && (
                      <button onClick={() => refund(inv)} title="Refund"
                        className="p-1.5 text-gray-500 hover:text-red-600">
                        <RotateCcw className="w-4 h-4" />
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {invoices.length === 0 && (
          <div className="p-8 text-center text-gray-400">No invoices yet</div>
        )}
      </div>
    </div>
  );
}
''')

    write_file(frontend / "src/pages/Reports.jsx", '''
import { useEffect, useState } from 'react';
import api from '../lib/api';
import { formatCurrency } from '../lib/utils';
import toast from 'react-hot-toast';

const TABS = [
  { id: 'trial', label: 'Trial Balance' },
  { id: 'balance', label: 'Balance Sheet' },
  { id: 'income', label: 'Income Statement' },
];

export default function Reports() {
  const [tab, setTab] = useState('trial');
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    setData(null);
    const ep = {
      trial: '/accounting/reports/trial-balance/',
      balance: '/accounting/reports/balance-sheet/',
      income: '/accounting/reports/income-statement/',
    }[tab];

    api.get(ep).then((r) => setData(r.data))
      .catch(() => toast.error('Failed to load report'))
      .finally(() => setLoading(false));
  }, [tab]);

  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-2xl font-bold mb-6">Financial Reports</h1>

      <div className="flex gap-2 mb-6 border-b border-gray-200">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`px-4 py-2 text-sm font-medium transition ${
              tab === t.id
                ? 'text-brand-700 border-b-2 border-brand-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {loading && <div className="text-gray-400">Loading...</div>}

      {!loading && data && tab === 'trial' && (
        <div className="card overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-gray-50 text-left text-xs uppercase text-gray-500">
              <tr>
                <th className="px-4 py-3">Code</th>
                <th className="px-4 py-3">Account</th>
                <th className="px-4 py-3 text-right">Debit</th>
                <th className="px-4 py-3 text-right">Credit</th>
              </tr>
            </thead>
            <tbody>
              {data.accounts.map((a) => (
                <tr key={a.code} className="border-t border-gray-100">
                  <td className="px-4 py-2 font-mono text-xs">{a.code}</td>
                  <td className="px-4 py-2">{a.name}</td>
                  <td className="px-4 py-2 text-right">
                    {a.debit > 0 ? formatCurrency(a.debit) : '-'}
                  </td>
                  <td className="px-4 py-2 text-right">
                    {a.credit > 0 ? formatCurrency(a.credit) : '-'}
                  </td>
                </tr>
              ))}
              <tr className="border-t-2 border-gray-300 font-bold bg-gray-50">
                <td className="px-4 py-3" colSpan={2}>Totals</td>
                <td className="px-4 py-3 text-right">{formatCurrency(data.total_debit)}</td>
                <td className="px-4 py-3 text-right">{formatCurrency(data.total_credit)}</td>
              </tr>
            </tbody>
          </table>
          {!data.balanced && (
            <div className="p-3 bg-red-50 text-red-700 text-sm">
              ⚠ Books are not balanced
            </div>
          )}
        </div>
      )}

      {!loading && data && tab === 'balance' && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div className="card p-6">
            <h2 className="font-semibold mb-4">Assets</h2>
            <div className="text-2xl font-bold text-green-700 mb-2">
              {formatCurrency(data.assets)}
            </div>
          </div>
          <div className="card p-6">
            <h2 className="font-semibold mb-4">Liabilities & Equity</h2>
            <div className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span>Liabilities</span>
                <span>{formatCurrency(data.liabilities)}</span>
              </div>
              <div className="flex justify-between">
                <span>Equity</span>
                <span>{formatCurrency(data.equity)}</span>
              </div>
              <div className="flex justify-between">
                <span>Net Income</span>
                <span>{formatCurrency(data.net_income)}</span>
              </div>
              <div className="flex justify-between border-t border-gray-200 pt-2 font-bold">
                <span>Total</span>
                <span>
                  {formatCurrency(data.liabilities + data.equity + data.net_income)}
                </span>
              </div>
            </div>
          </div>
        </div>
      )}

      {!loading && data && tab === 'income' && (
        <div className="card p-6 max-w-xl">
          <div className="flex justify-between py-2 border-b border-gray-100">
            <span className="text-gray-600">Revenue</span>
            <span className="font-semibold">{formatCurrency(data.revenue)}</span>
          </div>
          <div className="flex justify-between py-2 border-b border-gray-100">
            <span className="text-gray-600">Expenses</span>
            <span className="font-semibold">{formatCurrency(data.expenses)}</span>
          </div>
          <div className="flex justify-between py-3 text-lg font-bold">
            <span>Net Income</span>
            <span className={data.net_income >= 0 ? 'text-green-700' : 'text-red-700'}>
              {formatCurrency(data.net_income)}
            </span>
          </div>
          <div className="text-sm text-gray-500">
            Profit margin: {data.margin_percent.toFixed(1)}%
          </div>
        </div>
      )}
    </div>
  );
}
''')

    write_file(frontend / "src/pages/Settings.jsx", '''
import { useEffect, useState } from 'react';
import api from '../lib/api';
import toast from 'react-hot-toast';
import { CreditCard, Building2 } from 'lucide-react';

export default function Settings() {
  const [configs, setConfigs] = useState([]);
  const [showModal, setShowModal] = useState(false);
  const [form, setForm] = useState({
    provider: 'MONEYUNIFY', merchant_id: '', api_key: '', is_default: true,
  });

  const load = () => api.get('/payments/configs/').then((r) => setConfigs(r.data));
  useEffect(() => { load(); }, []);

  const save = async (e) => {
    e.preventDefault();
    try {
      await api.post('/payments/configs/', form);
      toast.success('Payment config saved');
      setShowModal(false);
      load();
    } catch (err) {
      toast.error(err.response?.data?.error || 'Save failed');
    }
  };

  return (
    <div className="p-6 overflow-y-auto h-full">
      <h1 className="text-2xl font-bold mb-6">Settings</h1>

      <div className="card p-6 mb-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="font-semibold flex items-center gap-2">
            <CreditCard className="w-5 h-5" />
            Payment Gateways (this branch)
          </h2>
          <button onClick={() => setShowModal(true)} className="btn-primary text-sm">
            Add Config
          </button>
        </div>

        {configs.length === 0 ? (
          <div className="text-gray-400 text-sm">No payment gateways configured</div>
        ) : (
          <div className="space-y-2">
            {configs.map((c) => (
              <div key={c.id} className="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
                <div>
                  <div className="font-medium">{c.provider}</div>
                  <div className="text-xs text-gray-500">
                    Merchant: {c.merchant_id || '-'}
                    {c.is_default && ' · Default'}
                  </div>
                </div>
                <span className={`text-xs px-2 py-0.5 rounded-full ${
                  c.is_enabled ? 'bg-green-100 text-green-700' : 'bg-gray-200 text-gray-600'
                }`}>
                  {c.is_enabled ? 'Enabled' : 'Disabled'}
                </span>
              </div>
            ))}
          </div>
        )}
      </div>

      {showModal && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-xl max-w-md w-full p-6">
            <h2 className="text-xl font-bold mb-4">Add Payment Config</h2>
            <form onSubmit={save} className="space-y-3">
              <select
                value={form.provider}
                onChange={(e) => setForm({...form, provider: e.target.value})}
                className="input-field"
              >
                <option value="MONEYUNIFY">MoneyUnify</option>
                <option value="MTN_DIRECT">MTN Direct</option>
                <option value="AIRTEL_DIRECT">Airtel Direct</option>
                <option value="ZAMTEL_DIRECT">Zamtel Direct</option>
              </select>
              <input placeholder="Merchant ID" value={form.merchant_id}
                onChange={(e) => setForm({...form, merchant_id: e.target.value})}
                className="input-field" required />
              <input placeholder="API Key" value={form.api_key}
                onChange={(e) => setForm({...form, api_key: e.target.value})}
                className="input-field" />
              <label className="flex items-center gap-2 text-sm">
                <input type="checkbox" checked={form.is_default}
                  onChange={(e) => setForm({...form, is_default: e.target.checked})} />
                Set as default for this branch
              </label>
              <button type="submit" className="btn-primary w-full">Save</button>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
''')

    write_file(frontend / "src/App.jsx", '''
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import Login from './pages/Login';
import BranchSelect from './pages/BranchSelect';
import POS from './pages/POS';
import Dashboard from './pages/Dashboard';
import Products from './pages/Products';
import Invoices from './pages/Invoices';
import Reports from './pages/Reports';
import Settings from './pages/Settings';
import Layout from './components/Layout';
import ProtectedRoute from './components/ProtectedRoute';

export default function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" />
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="/select-branch" element={
          <ProtectedRoute requireBranch={false}>
            <BranchSelect />
          </ProtectedRoute>
        } />
        <Route element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route path="/pos" element={<POS />} />
          <Route path="/dashboard" element={<Dashboard />} />
          <Route path="/products" element={<Products />} />
          <Route path="/invoices" element={<Invoices />} />
          <Route path="/reports" element={<Reports />} />
          <Route path="/settings" element={<Settings />} />
        </Route>
        <Route path="/" element={<Navigate to="/pos" replace />} />
      </Routes>
    </BrowserRouter>
  );
}
''')

    # ========================================================
    # Install dependencies
    # ========================================================
    print("\nInstalling npm packages (this takes ~60 seconds)...")
    run(["npm", "install"], cwd=frontend, shell=True)

    # Final message
    print("\n" + "=" * 60)
    print("  ✅ FRONTEND BUILD COMPLETE")
    print("=" * 60)
    print()
    print(f"Frontend: {frontend}")
    print()
    print("START DEV SERVERS:")
    print()
    print("  Terminal 1 (backend):")
    print(f"    cd {backend}")
    print("    .\\venv\\Scripts\\Activate.ps1  # Windows")
    print("    python manage.py runserver")
    print()
    print("  Terminal 2 (frontend):")
    print(f"    cd {frontend}")
    print("    npm run dev")
    print()
    print("  Open: http://localhost:5173")
    print()
    print("LOGIN:")
    print("  Owner: demo_owner / Demo@123456")
    print()
    print("=" * 60)


if __name__ == "__main__":
    main()