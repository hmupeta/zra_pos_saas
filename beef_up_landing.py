from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
landing_path = BACKEND_PATH / "templates" / "pos" / "landing.html"

landing_html = '''
<!doctype html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nimbus POS - Multi-Branch Retail SaaS for Zambia</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://unpkg.com/alpinejs@3.13.10/dist/cdn.min.js"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .glass { background: rgba(255, 255, 255, 0.8); backdrop-filter: blur(12px); }
    .bg-grid { background-image: radial-gradient(#e5e7eb 1px, transparent 1px); background-size: 40px 40px; }
    .gradient-text { background: linear-gradient(to right, #4f46e5, #9333ea); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }
  </style>
</head>
<body class="text-slate-800 antialiased bg-white" x-data="landingApp()" x-init="init()">

  <!-- Navbar -->
  <nav class="fixed w-full z-50 glass border-b border-gray-100 transition-all duration-300">
    <div class="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
      <div class="flex items-center gap-2">
        <div class="w-9 h-9 rounded-xl bg-indigo-600 flex items-center justify-center text-white shadow-lg shadow-indigo-200">
          <i data-lucide="zap" class="w-5 h-5"></i>
        </div>
        <span class="text-xl font-bold tracking-tight text-slate-900">Nimbus POS</span>
      </div>
      <div class="hidden md:flex gap-8 items-center font-medium text-sm text-gray-600">
        <a href="#challenges" class="hover:text-indigo-600 transition">Why Nimbus</a>
        <a href="#features" class="hover:text-indigo-600 transition">Features</a>
        <a href="#how-it-works" class="hover:text-indigo-600 transition">How it Works</a>
        <a href="#industries" class="hover:text-indigo-600 transition">Industries</a>
        <a href="#pricing" class="hover:text-indigo-600 transition">Pricing</a>
        <a href="/login" class="hover:text-indigo-600 transition">Login</a>
        <button @click="showSignup = true" class="bg-indigo-600 text-white px-5 py-2.5 rounded-lg hover:bg-indigo-700 transition shadow-md shadow-indigo-200">Start Free Trial</button>
      </div>
    </div>
  </nav>

  <!-- Hero Section -->
  <section class="pt-32 pb-24 px-6 bg-grid relative overflow-hidden">
    <div class="absolute inset-0 bg-gradient-to-b from-indigo-50/80 via-white to-white -z-10"></div>
    <div class="max-w-7xl mx-auto text-center relative z-10">
      <div class="inline-flex items-center gap-2 px-4 py-1.5 rounded-full bg-indigo-100/80 text-indigo-700 text-xs font-bold uppercase tracking-wider mb-8 border border-indigo-200">
        <span class="w-2 h-2 rounded-full bg-indigo-600 animate-pulse"></span> Built for Multi-Branch Retail
      </div>
      <h1 class="text-5xl md:text-7xl font-extrabold text-slate-900 tracking-tight leading-[1.1] mb-8">
        Stop managing branches.<br/>
        <span class="gradient-text">Start scaling them.</span>
      </h1>
      <p class="text-lg md:text-xl text-gray-500 max-w-3xl mx-auto mb-10 leading-relaxed">
        The all-in-one SaaS platform for Zambian retail. Centralize inventory, sync sales in real-time, accept mobile money, and stay 100% ZRA compliant — from one powerful dashboard.
      </p>
      <div class="flex flex-col sm:flex-row justify-center gap-4 mb-16">
        <button @click="showSignup = true" class="bg-indigo-600 text-white px-8 py-4 rounded-xl font-bold text-lg hover:bg-indigo-700 transition shadow-xl shadow-indigo-200/60 flex items-center justify-center gap-2">
          <i data-lucide="rocket" class="w-5 h-5"></i> Start 14-Day Free Trial
        </button>
        <a href="/login" class="bg-white text-slate-700 border-2 border-gray-100 px-8 py-4 rounded-xl font-bold text-lg hover:border-indigo-100 hover:bg-gray-50 transition flex items-center justify-center gap-2">
          <i data-lucide="monitor" class="w-5 h-5"></i> Access Dashboard
        </a>
      </div>

      <!-- Trust Signals -->
      <div class="grid grid-cols-2 md:grid-cols-4 gap-6 max-w-4xl mx-auto border-t border-gray-100 pt-10">
        <div class="text-center">
          <div class="text-3xl font-bold text-slate-900">99.9%</div>
          <div class="text-sm text-gray-500 mt-1 font-medium">Server Uptime</div>
        </div>
        <div class="text-center">
          <div class="text-3xl font-bold text-slate-900">50K+</div>
          <div class="text-sm text-gray-500 mt-1 font-medium">Daily Transactions</div>
        </div>
        <div class="text-center">
          <div class="text-3xl font-bold text-slate-900">100%</div>
          <div class="text-sm text-gray-500 mt-1 font-medium">ZRA Compliant</div>
        </div>
        <div class="text-center">
          <div class="text-3xl font-bold text-slate-900">24/7</div>
          <div class="text-sm text-gray-500 mt-1 font-medium">Local Support</div>
        </div>
      </div>
    </div>
  </section>

  <!-- Challenges / Pain Points Section -->
  <section id="challenges" class="py-24 bg-slate-50">
    <div class="max-w-7xl mx-auto px-6">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Running multiple branches shouldn't feel like guesswork</h2>
        <p class="text-gray-500 max-w-2xl mx-auto text-lg">Without a unified system, growth creates blind spots. Here is what we solve.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        <div class="bg-white p-8 rounded-2xl border border-gray-100 shadow-sm">
          <div class="w-12 h-12 bg-red-50 text-red-500 rounded-xl flex items-center justify-center mb-4">
            <i data-lucide="eye-off" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">No real-time visibility</h3>
          <p class="text-gray-500 text-sm leading-relaxed">You don't know today's sales at each branch until end-of-day reports arrive — often manually compiled.</p>
        </div>
        <div class="bg-white p-8 rounded-2xl border border-gray-100 shadow-sm">
          <div class="w-12 h-12 bg-orange-50 text-orange-500 rounded-xl flex items-center justify-center mb-4">
            <i data-lucide="alert-triangle" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">Inconsistent pricing</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Different branches charge different prices for the same item because product lists are managed separately.</p>
        </div>
        <div class="bg-white p-8 rounded-2xl border border-gray-100 shadow-sm">
          <div class="w-12 h-12 bg-blue-50 text-blue-500 rounded-xl flex items-center justify-center mb-4">
            <i data-lucide="arrow-left-right" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">No inter-branch stock transfers</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Branch A runs out of stock while Branch B has excess — but there's no system to facilitate transfers.</p>
        </div>
        <div class="bg-white p-8 rounded-2xl border border-gray-100 shadow-sm">
          <div class="w-12 h-12 bg-purple-50 text-purple-500 rounded-xl flex items-center justify-center mb-4">
            <i data-lucide="users" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">Separate customer databases</h3>
          <p class="text-gray-500 text-sm leading-relaxed">A loyal customer at Branch A is unknown to Branch B — a lost loyalty opportunity.</p>
        </div>
        <div class="bg-white p-8 rounded-2xl border border-gray-100 shadow-sm">
          <div class="w-12 h-12 bg-yellow-50 text-yellow-600 rounded-xl flex items-center justify-center mb-4">
            <i data-lucide="calculator" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">Manual consolidated reporting</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Someone must pull reports from each branch and merge them — weekly or monthly.</p>
        </div>
        <div class="bg-white p-8 rounded-2xl border border-gray-100 shadow-sm">
          <div class="w-12 h-12 bg-pink-50 text-pink-500 rounded-xl flex items-center justify-center mb-4">
            <i data-lucide="megaphone" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">Inconsistent promotions</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Running the same promotion across all branches simultaneously is difficult to coordinate.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Core Features Grid -->
  <section id="features" class="py-24 bg-white">
    <div class="max-w-7xl mx-auto px-6">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Everything you need to run a modern retail chain</h2>
        <p class="text-gray-500 max-w-2xl mx-auto text-lg">One platform. Every tool. Zero friction.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <!-- Feature 1 -->
        <div class="group p-8 rounded-2xl bg-white border border-gray-100 hover:shadow-xl hover:border-indigo-100 transition-all duration-300">
          <div class="w-12 h-12 bg-indigo-50 text-indigo-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <i data-lucide="building-2" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Centralized Multi-Branch Control</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Manage every location from one HQ dashboard. Compare performance, push pricing updates instantly, and monitor sales in real-time.</p>
        </div>
        <!-- Feature 2 -->
        <div class="group p-8 rounded-2xl bg-white border border-gray-100 hover:shadow-xl hover:border-indigo-100 transition-all duration-300">
          <div class="w-12 h-12 bg-emerald-50 text-emerald-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <i data-lucide="arrow-right-left" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Inter-Branch Stock Transfers</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Move stock between locations with a full audit trail. Inventory counts update automatically on both sides when a transfer is confirmed.</p>
        </div>
        <!-- Feature 3 -->
        <div class="group p-8 rounded-2xl bg-white border border-gray-100 hover:shadow-xl hover:border-indigo-100 transition-all duration-300">
          <div class="w-12 h-12 bg-purple-50 text-purple-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <i data-lucide="database" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Multi-Tenant Data Isolation</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Each business operates in its own secure silo. Your data, customers, and finances are never shared with other tenants.</p>
        </div>
        <!-- Feature 4 -->
        <div class="group p-8 rounded-2xl bg-white border border-gray-100 hover:shadow-xl hover:border-indigo-100 transition-all duration-300">
          <div class="w-12 h-12 bg-orange-50 text-orange-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <i data-lucide="layout-dashboard" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Unified Financial Reporting</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Consolidated profit & loss, sales summaries, and inventory valuations across all branches with a single click. No manual merging.</p>
        </div>
        <!-- Feature 5 -->
        <div class="group p-8 rounded-2xl bg-white border border-gray-100 hover:shadow-xl hover:border-indigo-100 transition-all duration-300">
          <div class="w-12 h-12 bg-blue-50 text-blue-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <i data-lucide="users" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Centralized Customer Database</h3>
          <p class="text-gray-500 text-sm leading-relaxed">A customer registered at any branch is recognized at every branch. Loyalty points, purchase history, and credit limits follow them everywhere.</p>
        </div>
        <!-- Feature 6 -->
        <div class="group p-8 rounded-2xl bg-white border border-gray-100 hover:shadow-xl hover:border-indigo-100 transition-all duration-300">
          <div class="w-12 h-12 bg-rose-50 text-rose-600 rounded-xl flex items-center justify-center mb-6 group-hover:scale-110 transition-transform">
            <i data-lucide="shield-check" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Branch-Level Access Control</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Cashiers see only their till. Managers see their branch. Owners see everything. Granular role-based permissions keep your data secure.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- How It Works -->
  <section id="how-it-works" class="py-24 bg-slate-900 text-white overflow-hidden relative">
    <div class="absolute inset-0 bg-grid opacity-10"></div>
    <div class="max-w-7xl mx-auto px-6 relative z-10">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold mb-4">From chaos to clarity in four steps</h2>
        <p class="text-slate-400 max-w-2xl mx-auto text-lg">Setting up your retail empire shouldn't require a consultant.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-4 gap-8">
        <div class="relative">
          <div class="text-6xl font-black text-slate-800 absolute -top-8 -left-2 -z-10">01</div>
          <div class="w-12 h-12 bg-indigo-500/20 text-indigo-400 rounded-xl flex items-center justify-center mb-4 border border-indigo-500/30">
            <i data-lucide="map-pin" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">Set Up Locations</h3>
          <p class="text-slate-400 text-sm">Add your branches with addresses, contacts, and operating hours. Each gets its own settings while sharing a master catalog.</p>
        </div>
        <div class="relative">
          <div class="text-6xl font-black text-slate-800 absolute -top-8 -left-2 -z-10">02</div>
          <div class="w-12 h-12 bg-emerald-500/20 text-emerald-400 rounded-xl flex items-center justify-center mb-4 border border-emerald-500/30">
            <i data-lucide="user-plus" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">Assign Users</h3>
          <p class="text-slate-400 text-sm">Add staff to their respective branches. Managers get multi-branch access; cashiers stay locked to their till.</p>
        </div>
        <div class="relative">
          <div class="text-6xl font-black text-slate-800 absolute -top-8 -left-2 -z-10">03</div>
          <div class="w-12 h-12 bg-purple-500/20 text-purple-400 rounded-xl flex items-center justify-center mb-4 border border-purple-500/30">
            <i data-lucide="refresh-cw" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">Sync Inventory</h3>
          <p class="text-slate-400 text-sm">Upload products once and distribute to locations. Set initial stock levels per branch and let transfers handle the rest.</p>
        </div>
        <div class="relative">
          <div class="text-6xl font-black text-slate-800 absolute -top-8 -left-2 -z-10">04</div>
          <div class="w-12 h-12 bg-orange-500/20 text-orange-400 rounded-xl flex items-center justify-center mb-4 border border-orange-500/30">
            <i data-lucide="bar-chart" class="w-6 h-6"></i>
          </div>
          <h3 class="font-bold text-lg mb-2">Monitor & Grow</h3>
          <p class="text-slate-400 text-sm">Watch sales roll in from HQ. Respond to opportunities and issues instantly with real-time data.</p>
        </div>
      </div>
    </div>
  </section>

  <!-- Who Uses Nimbus -->
  <section id="industries" class="py-24 bg-white">
    <div class="max-w-7xl mx-auto px-6">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Built for every retail vertical</h2>
        <p class="text-gray-500 max-w-2xl mx-auto text-lg">From a single kiosk to a nationwide franchise, Nimbus adapts to your business.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <div class="flex items-center gap-4 p-4 rounded-xl bg-gray-50 border border-gray-100">
          <i data-lucide="shopping-basket" class="w-6 h-6 text-indigo-600"></i>
          <div>
            <div class="font-bold text-sm">Supermarkets & Groceries</div>
            <div class="text-xs text-gray-500">Centralized pricing, category management, consolidated procurement</div>
          </div>
        </div>
        <div class="flex items-center gap-4 p-4 rounded-xl bg-gray-50 border border-gray-100">
          <i data-lucide="shirt" class="w-6 h-6 text-indigo-600"></i>
          <div>
            <div class="font-bold text-sm">Fashion & Apparel</div>
            <div class="text-xs text-gray-500">Centralized catalog, cross-branch stock visibility, unified customer DB</div>
          </div>
        </div>
        <div class="flex items-center gap-4 p-4 rounded-xl bg-gray-50 border border-gray-100">
          <i data-lucide="pill" class="w-6 h-6 text-indigo-600"></i>
          <div>
            <div class="font-bold text-sm">Pharmacies</div>
            <div class="text-xs text-gray-500">Batch/expiry tracking, regulatory compliance reporting, inter-branch transfer</div>
          </div>
        </div>
        <div class="flex items-center gap-4 p-4 rounded-xl bg-gray-50 border border-gray-100">
          <i data-lucide="utensils" class="w-6 h-6 text-indigo-600"></i>
          <div>
            <div class="font-bold text-sm">Restaurants & Cafes</div>
            <div class="text-xs text-gray-500">Standardized menus, branch sales comparison, franchise reporting</div>
          </div>
        </div>
        <div class="flex items-center gap-4 p-4 rounded-xl bg-gray-50 border border-gray-100">
          <i data-lucide="cpu" class="w-6 h-6 text-indigo-600"></i>
          <div>
            <div class="font-bold text-sm">Electronics Retailers</div>
            <div class="text-xs text-gray-500">Serial/IMEI tracking, warranty management, inter-branch order fulfillment</div>
          </div>
        </div>
        <div class="flex items-center gap-4 p-4 rounded-xl bg-gray-50 border border-gray-100">
          <i data-lucide="warehouse" class="w-6 h-6 text-indigo-600"></i>
          <div>
            <div class="font-bold text-sm">Wholesale Distributors</div>
            <div class="text-xs text-gray-500">Regional warehouses, main depot + satellite tracking, van sales routes</div>
          </div>
        </div>
      </div>
    </div>
  </section>

  <!-- Pricing Section -->
  <section id="pricing" class="py-24 bg-slate-50">
    <div class="max-w-7xl mx-auto px-6">
      <div class="text-center mb-16">
        <h2 class="text-3xl md:text-4xl font-bold text-slate-900 mb-4">Simple, transparent pricing</h2>
        <p class="text-gray-500 max-w-2xl mx-auto text-lg">Start with a 14-day free trial. No credit card required.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8 max-w-5xl mx-auto">
        <!-- Basic -->
        <div class="bg-white rounded-3xl p-8 border border-gray-100 shadow-sm flex flex-col">
          <div class="font-bold text-lg text-slate-900 mb-1">Basic</div>
          <div class="text-sm text-gray-500 mb-6">For single-location shops getting started</div>
          <div class="text-4xl font-extrabold text-slate-900 mb-6">K500<span class="text-lg text-gray-400 font-medium">/mo</span></div>
          <ul class="space-y-3 mb-8 flex-1">
            <li class="flex items-center gap-2 text-sm text-gray-600"><i data-lucide="check" class="w-4 h-4 text-green-500"></i> 1 Branch</li>
            <li class="flex items-center gap-2 text-sm text-gray-600"><i data-lucide="check" class="w-4 h-4 text-green-500"></i> Up to 5 Users</li>
            <li class="flex items-center gap-2 text-sm text-gray-600"><i data-lucide="check" class="w-4 h-4 text-green-500"></i> POS & Inventory</li>
            <li class="flex items-center gap-2 text-sm text-gray-600"><i data-lucide="check" class="w-4 h-4 text-green-500"></i> ZRA Smart Invoice</li>
          </ul>
          <button @click="showSignup = true" class="w-full py-3 rounded-xl border-2 border-gray-200 font-bold text-slate-700 hover:border-indigo-600 hover:text-indigo-600 transition">Choose Basic</button>
        </div>
        <!-- Pro -->
        <div class="bg-indigo-600 rounded-3xl p-8 border border-indigo-500 shadow-2xl shadow-indigo-200 flex flex-col relative transform md:-translate-y-4">
          <div class="absolute top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-gradient-to-r from-amber-400 to-orange-500 text-white text-xs font-bold px-4 py-1 rounded-full uppercase tracking-wider">Most Popular</div>
          <div class="font-bold text-lg text-white mb-1">Professional</div>
          <div class="text-sm text-indigo-200 mb-6">For growing multi-branch retailers</div>
          <div class="text-4xl font-extrabold text-white mb-6">K1,500<span class="text-lg text-indigo-200 font-medium">/mo</span></div>
          <ul class="space-y-3 mb-8 flex-1">
            <li class="flex items-center gap-2 text-sm text-indigo-100"><i data-lucide="check" class="w-4 h-4 text-indigo-300"></i> Up to 5 Branches</li>
            <li class="flex items-center gap-2 text-sm text-indigo-100"><i data-lucide="check" class="w-4 h-4 text-indigo-300"></i> Up to 25 Users</li>
            <li class="flex items-center gap-2 text-sm text-indigo-100"><i data-lucide="check" class="w-4 h-4 text-indigo-300"></i> Multi-Branch Reports</li>
            <li class="flex items-center gap-2 text-sm text-indigo-100"><i data-lucide="check" class="w-4 h-4 text-indigo-300"></i> Full Accounting Module</li>
            <li class="flex items-center gap-2 text-sm text-indigo-100"><i data-lucide="check" class="w-4 h-4 text-indigo-300"></i> API Access</li>
          </ul>
          <button @click="showSignup = true" class="w-full py-3 rounded-xl bg-white text-indigo-600 font-bold hover:bg-gray-50 transition">Choose Professional</button>
        </div>
        <!-- Enterprise -->
        <div class="bg-white rounded-3xl p-8 border border-gray-100 shadow-sm flex flex-col">
          <div class="font-bold text-lg text-slate-900 mb-1">Enterprise</div>
          <div class="text-sm text-gray-500 mb-6">For nationwide franchises & chains</div>
          <div class="text-4xl font-extrabold text-slate-900 mb-6">Custom</div>
          <ul class="space-y-3 mb-8 flex-1">
            <li class="flex items-center gap-2 text-sm text-gray-600"><i data-lucide="check" class="w-4 h-4 text-green-500"></i> Unlimited Branches</li>
            <li class="flex items-center gap-2 text-sm text-gray-600"><i data-lucide="check" class="w-4 h-4 text-green-500"></i> Unlimited Users</li>
            <li class="flex items-center gap-2 text-sm text-gray-600"><i data-lucide="check" class="w-4 h-4 text-green-500"></i> Dedicated Account Manager</li>
            <li class="flex items-center gap-2 text-sm text-gray-600"><i data-lucide="check" class="w-4 h-4 text-green-500"></i> Custom SLAs & Onboarding</li>
          </ul>
          <button class="w-full py-3 rounded-xl border-2 border-gray-200 font-bold text-slate-700 hover:border-slate-900 transition">Contact Sales</button>
        </div>
      </div>
    </div>
  </section>

  <!-- Testimonial / Social Proof -->
  <section class="py-24 bg-white">
    <div class="max-w-4xl mx-auto px-6 text-center">
      <div class="flex justify-center gap-1 mb-6 text-amber-400">
        <i data-lucide="star" class="fill-current w-6 h-6"></i>
        <i data-lucide="star" class="fill-current w-6 h-6"></i>
        <i data-lucide="star" class="fill-current w-6 h-6"></i>
        <i data-lucide="star" class="fill-current w-6 h-6"></i>
        <i data-lucide="star" class="fill-current w-6 h-6"></i>
      </div>
      <blockquote class="text-2xl md:text-3xl font-medium text-slate-900 leading-snug mb-8">
        "I manage three branches with Nimbus. The inventory and HRM features save me hours every week. Worth every shilling."
      </blockquote>
      <div class="flex items-center justify-center gap-4">
        <div class="w-12 h-12 bg-indigo-100 rounded-full flex items-center justify-center text-indigo-700 font-bold text-lg">
          MJ
        </div>
        <div class="text-left">
          <div class="font-bold text-slate-900">Mohamed Jama</div>
          <div class="text-sm text-gray-500">CEO, Multi-Branch Retailer</div>
        </div>
      </div>
    </div>
  </section>

  <!-- CTA Banner -->
  <section class="py-24 bg-indigo-600 relative overflow-hidden">
    <div class="absolute inset-0 bg-grid opacity-10"></div>
    <div class="max-w-4xl mx-auto px-6 text-center relative z-10">
      <h2 class="text-3xl md:text-4xl font-bold text-white mb-4">Ready to connect your stores?</h2>
      <p class="text-indigo-100 mb-8 text-lg">Join hundreds of shops modernizing their operations. Start your free trial today.</p>
      <button @click="showSignup = true" class="bg-white text-indigo-600 px-10 py-4 rounded-xl font-bold text-lg hover:bg-gray-50 transition shadow-xl">Start Free Trial</button>
    </div>
  </section>

  <!-- Footer -->
  <footer class="bg-slate-900 text-slate-400 py-12 border-t border-slate-800">
    <div class="max-w-7xl mx-auto px-6 flex flex-col md:flex-row justify-between items-center">
      <div class="mb-4 md:mb-0 flex items-center gap-2">
        <div class="w-6 h-6 rounded bg-indigo-500 flex items-center justify-center text-white">
          <i data-lucide="zap" class="w-4 h-4"></i>
        </div>
        <span class="text-white font-bold">Nimbus POS</span>
      </div>
      <div class="flex gap-6 text-sm">
        <a href="/terms" class="hover:text-white transition">Terms of Service</a>
        <a href="#" class="hover:text-white transition">Privacy Policy</a>
        <a href="#" class="hover:text-white transition">Contact Support</a>
      </div>
      <div class="mt-4 md:mt-0 text-sm">&copy; 2026 Nimbus SaaS. All rights reserved.</div>
    </div>
  </footer>

  <!-- Onboarding / Signup Modal -->
  <div x-show="showSignup" x-cloak class="fixed inset-0 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-2xl max-w-lg w-full p-8 shadow-2xl relative max-h-[90vh] overflow-y-auto" @click.away="showSignup = false">
      <button @click="showSignup = false" class="absolute top-4 right-4 text-gray-400 hover:text-gray-700"><i data-lucide="x" class="w-6 h-6"></i></button>

      <div x-show="!success">
        <h2 class="text-2xl font-bold text-slate-900 mb-2">Apply for Nimbus POS</h2>
        <p class="text-gray-500 text-sm mb-6">Tell us about your business. Our team reviews applications within 24 hours.</p>

        <form @submit.prevent="submitSignup()" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-1">Business Name</label>
            <input type="text" x-model="form.business_name" class="w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" required>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Your Full Name</label>
            <input type="text" x-model="form.contact_name" class="w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" required>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Email</label>
              <input type="email" x-model="form.contact_email" class="w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" required>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Phone</label>
              <input type="tel" x-model="form.contact_phone" class="w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" required>
            </div>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Number of Branches</label>
              <select x-model="form.requested_branch_count" class="w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
                <option value="1">1 Branch</option>
                <option value="2-5">2-5 Branches</option>
                <option value="6-10">6-10 Branches</option>
                <option value="10+">10+ Branches</option>
              </select>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Plan Interested In</label>
              <select x-model="form.plan_code" class="w-full px-4 py-2.5 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none">
                <option value="TRIAL">Free Trial</option>
                <option value="BASIC">Basic</option>
                <option value="PRO">Professional</option>
                <option value="ENTERPRISE">Enterprise</option>
              </select>
            </div>
          </div>
          <div class="flex items-start gap-2 pt-2">
            <input type="checkbox" required class="mt-1">
            <label class="text-xs text-gray-500 leading-tight">I agree to the <a href="/terms" target="_blank" class="text-indigo-600 hover:underline">Terms of Service</a> and Privacy Policy.</label>
          </div>
          <button type="submit" class="w-full bg-indigo-600 text-white py-3.5 rounded-xl font-bold hover:bg-indigo-700 transition shadow-lg shadow-indigo-200" :disabled="loading">
            <span x-text="loading ? 'Submitting Application...' : 'Submit Application'"></span>
          </button>
        </form>
      </div>

      <div x-show="success" class="text-center py-8">
        <div class="w-20 h-20 bg-green-50 text-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
          <i data-lucide="check-circle" class="w-10 h-10"></i>
        </div>
        <h2 class="text-2xl font-bold text-slate-900 mb-2">Application Received!</h2>
        <p class="text-gray-500 mb-6">Thank you! Our onboarding team will review your business details and send your login credentials via email within 24 hours.</p>
        <button @click="showSignup = false" class="bg-slate-100 text-slate-700 px-8 py-2.5 rounded-lg font-medium hover:bg-slate-200">Close</button>
      </div>
    </div>
  </div>

  <script>
    function landingApp() {
      return {
        showSignup: false,
        loading: false,
        success: false,
        form: { business_name: '', contact_name: '', contact_email: '', contact_phone: '', requested_branch_count: '1', plan_code: 'TRIAL' },
        init() {
          const urlParams = new URLSearchParams(window.location.search);
          if (urlParams.has('signup') || window.location.hash === '#signup') {
            this.showSignup = true;
          }
        },
        async submitSignup() {
          this.loading = true;
          try {
            const res = await fetch('/api/saas/signup/', {
              method: 'POST',
              headers: { 'Content-Type': 'application/json' },
              body: JSON.stringify(this.form)
            });
            if (res.ok) {
              this.success = true;
            } else {
              const data = await res.json();
              alert(data.error || 'Something went wrong');
            }
          } catch(e) {
            alert('Network error. Please try again.');
          } finally {
            this.loading = false;
          }
        }
      }
    }
    document.addEventListener('DOMContentLoaded', () => { lucide.createIcons(); });
  </script>
</body>
</html>
'''

landing_path.write_text(landing_html.strip(), encoding="utf-8")
print("✅ Rebuilt landing.html with expanded content from source materials.")