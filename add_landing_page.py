import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update Views (Landing & Terms)
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")

# Change index to redirect to landing
if "def landing_page" not in web_content:
    web_content = web_content.replace(
        "def index(request):\n    return redirect(\"/login\")",
        "def index(request):\n    return redirect(\"/welcome\")"
    )
    web_content += """

def landing_page(request):
    return render(request, "pos/landing.html")

def terms_page(request):
    return render(request, "pos/terms.html")
"""
    views_web.write_text(web_content, encoding="utf-8")
print("✅ Updated core/views_web.py")

# ============================================================
# 2. Update URLs
# ============================================================
urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")

if "/welcome" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('welcome', views_web.landing_page, name='landing'),\n    path('terms', views_web.terms_page, name='terms'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")
print("✅ Updated core/urls_web.py")

# ============================================================
# 3. Create Terms & Conditions Page
# ============================================================
terms_path = BACKEND_PATH / "templates" / "pos" / "terms.html"
terms_html = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Terms of Service - Nimbus POS</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
  <style>body { font-family: 'Inter', sans-serif; }</style>
</head>
<body class="bg-gray-50 text-slate-800 antialiased">
  <nav class="bg-white border-b border-gray-200 py-4">
    <div class="max-w-4xl mx-auto px-4 flex justify-between items-center">
      <a href="/welcome" class="text-2xl font-bold text-indigo-600">Nimbus POS</a>
      <a href="/welcome" class="text-sm font-medium text-gray-600 hover:text-indigo-600">&larr; Back to Home</a>
    </div>
  </nav>

  <main class="max-w-4xl mx-auto px-4 py-12 bg-white shadow-sm border border-gray-100 my-8 rounded-xl">
    <h1 class="text-3xl font-bold mb-6">Terms of Service & Privacy Policy</h1>
    <p class="text-sm text-gray-500 mb-8">Last updated: November 2026</p>

    <div class="space-y-6 text-gray-700 leading-relaxed">
      <section>
        <h2 class="text-xl font-bold text-gray-900 mb-2">1. Agreement to Terms</h2>
        <p>By accessing or using Nimbus POS ("the Service"), you agree to be bound by these Terms. If you disagree with any part of the terms, you may not access the Service.</p>
      </section>

      <section>
        <h2 class="text-xl font-bold text-gray-900 mb-2">2. Multi-Tenant Architecture</h2>
        <p>Nimbus POS provides a multi-tenant environment. Your data (Sales, Inventory, Customers) is logically isolated from other businesses. However, you are responsible for maintaining the confidentiality of your account credentials and for all activities that occur under your account.</p>
      </section>

      <section>
        <h2 class="text-xl font-bold text-gray-900 mb-2">3. ZRA Compliance</h2>
        <p>Our system integrates with the ZRA Smart Invoice API to generate fiscal receipts. While we provide the technical integration, you are solely responsible for ensuring your TPIN, VSDC credentials, and tax declarations are accurate and legally compliant.</p>
      </section>

      <section>
        <h2 class="text-xl font-bold text-gray-900 mb-2">4. Subscription and Billing</h2>
        <p>Services are billed on a subscription basis. You will be billed in advance on a recurring and periodic basis (such as monthly or annually). We reserve the right to suspend or terminate your access if payment is not received.</p>
      </section>

      <section>
        <h2 class="text-xl font-bold text-gray-900 mb-2">5. Data Protection</h2>
        <p>We implement industry-standard security measures to protect your business data. We do not sell your customer data to third parties. You retain all rights to the data you input into the system.</p>
      </section>
    </div>
  </main>

  <footer class="text-center py-8 text-gray-500 text-sm">
    &copy; 2026 Nimbus POS. All rights reserved.
  </footer>
</body>
</html>
'''
terms_path.write_text(terms_html.strip(), encoding="utf-8")
print("✅ Created terms.html")

# ============================================================
# 4. Create the Landing Page (Hero, Features, Pricing, Onboarding)
# ============================================================
landing_path = BACKEND_PATH / "templates" / "pos" / "landing.html"
landing_html = '''
<!doctype html>
<html lang="en" class="scroll-smooth">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Nimbus POS - Modern Retail SaaS</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <script defer src="https://unpkg.com/alpinejs@3.13.10/dist/cdn.min.js"></script>
  <script src="https://unpkg.com/lucide@latest"></script>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">
  <style>
    body { font-family: 'Inter', sans-serif; }
    .glass { background: rgba(255, 255, 255, 0.7); backdrop-filter: blur(10px); }
    .bg-grid { background-image: radial-gradient(#e5e7eb 1px, transparent 1px); background-size: 40px 40px; }
  </style>
</head>
<body class="text-slate-800 antialiased bg-white" x-data="landingApp()">

  <!-- Navbar -->
  <nav class="fixed w-full z-50 glass border-b border-gray-100 transition-all">
    <div class="max-w-7xl mx-auto px-6 py-4 flex justify-between items-center">
      <div class="flex items-center gap-2">
        <div class="w-8 h-8 rounded-lg bg-indigo-600 flex items-center justify-center text-white">
          <i data-lucide="zap" class="w-5 h-5"></i>
        </div>
        <span class="text-xl font-bold tracking-tight text-slate-900">Nimbus POS</span>
      </div>
      <div class="hidden md:flex gap-8 items-center font-medium text-sm text-gray-600">
        <a href="#features" class="hover:text-indigo-600 transition">Features</a>
        <a href="#how-it-works" class="hover:text-indigo-600 transition">How it Works</a>
        <a href="#pricing" class="hover:text-indigo-600 transition">Pricing</a>
        <a href="/login" class="hover:text-indigo-600 transition">Login</a>
        <button @click="showSignup = true" class="bg-indigo-600 text-white px-5 py-2 rounded-lg hover:bg-indigo-700 transition shadow-md shadow-indigo-200">Start Free Trial</button>
      </div>
    </div>
  </nav>

  <!-- Hero Section -->
  <section class="pt-32 pb-20 px-6 bg-grid relative overflow-hidden">
    <div class="absolute inset-0 bg-gradient-to-b from-indigo-50/50 to-white -z-10"></div>
    <div class="max-w-7xl mx-auto text-center">
      <div class="inline-flex items-center gap-2 px-3 py-1 rounded-full bg-indigo-100 text-indigo-700 text-xs font-bold uppercase tracking-wide mb-6">
        <span class="w-2 h-2 rounded-full bg-indigo-600 animate-pulse"></span> ZRA Smart Invoice Ready
      </div>
      <h1 class="text-5xl md:text-7xl font-extrabold text-slate-900 tracking-tight leading-tight mb-6">
        The operating system for <br/>
        <span class="text-transparent bg-clip-text bg-gradient-to-r from-indigo-600 to-purple-600">modern retail.</span>
      </h1>
      <p class="text-lg md:text-xl text-gray-500 max-w-2xl mx-auto mb-10">
        Manage multiple branches, track inventory, accept mobile money, and stay 100% compliant with ZRA — all from one beautiful dashboard.
      </p>
      <div class="flex flex-col sm:flex-row justify-center gap-4">
        <button @click="showSignup = true" class="bg-indigo-600 text-white px-8 py-4 rounded-xl font-bold text-lg hover:bg-indigo-700 transition shadow-xl shadow-indigo-200/50">
          Start Free Trial
        </button>
        <a href="/login" class="bg-white text-slate-700 border border-gray-200 px-8 py-4 rounded-xl font-bold text-lg hover:bg-gray-50 transition flex items-center justify-center gap-2">
          <i data-lucide="log-in" class="w-5 h-5"></i> Access Dashboard
        </a>
      </div>
    </div>
  </section>

  <!-- Features Grid -->
  <section id="features" class="py-24 bg-white">
    <div class="max-w-7xl mx-auto px-6">
      <div class="text-center mb-16">
        <h2 class="text-3xl font-bold text-slate-900 mb-4">Everything you need to grow</h2>
        <p class="text-gray-500 max-w-xl mx-auto">Built for Zambian retail. From single-shop setups to nationwide franchises.</p>
      </div>
      <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <!-- Feature 1 -->
        <div class="p-8 rounded-2xl bg-gray-50 border border-gray-100 hover:shadow-lg transition">
          <div class="w-12 h-12 bg-indigo-100 text-indigo-600 rounded-xl flex items-center justify-center mb-6">
            <i data-lucide="shield-check" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">ZRA Compliant</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Auto-generate fiscal receipts with QR codes. Full integration with ZRA VSDC and Smart Invoice API.</p>
        </div>
        <!-- Feature 2 -->
        <div class="p-8 rounded-2xl bg-gray-50 border border-gray-100 hover:shadow-lg transition">
          <div class="w-12 h-12 bg-purple-100 text-purple-600 rounded-xl flex items-center justify-center mb-6">
            <i data-lucide="building" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Multi-Branch</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Manage multiple branches from a central HQ. Assign managers, track inter-branch transfers, and view consolidated reports.</p>
        </div>
        <!-- Feature 3 -->
        <div class="p-8 rounded-2xl bg-gray-50 border border-gray-100 hover:shadow-lg transition">
          <div class="w-12 h-12 bg-emerald-100 text-emerald-600 rounded-xl flex items-center justify-center mb-6">
            <i data-lucide="smartphone" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Mobile Money</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Accept MTN, Airtel, and Zamtel payments seamlessly at the till with automated reconciliation.</p>
        </div>
        <!-- Feature 4 -->
        <div class="p-8 rounded-2xl bg-gray-50 border border-gray-100 hover:shadow-lg transition">
          <div class="w-12 h-12 bg-orange-100 text-orange-600 rounded-xl flex items-center justify-center mb-6">
            <i data-lucide="bar-chart-2" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Live Analytics</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Beautiful charts showing daily sales, top-performing agents, and inventory movements in real time.</p>
        </div>
        <!-- Feature 5 -->
        <div class="p-8 rounded-2xl bg-gray-50 border border-gray-100 hover:shadow-lg transition">
          <div class="w-12 h-12 bg-pink-100 text-pink-600 rounded-xl flex items-center justify-center mb-6">
            <i data-lucide="book" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Double-Entry Accounting</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Built-in general ledger, chart of accounts, and financial statements. Know exactly where your money goes.</p>
        </div>
        <!-- Feature 6 -->
        <div class="p-8 rounded-2xl bg-gray-50 border border-gray-100 hover:shadow-lg transition">
          <div class="w-12 h-12 bg-blue-100 text-blue-600 rounded-xl flex items-center justify-center mb-6">
            <i data-lucide="users" class="w-6 h-6"></i>
          </div>
          <h3 class="text-xl font-bold mb-3">Customer Loyalty</h3>
          <p class="text-gray-500 text-sm leading-relaxed">Track buying history, manage credit limits, and reward loyal customers with an automated points system.</p>
        </div>
      </div>
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

  <!-- Onboarding Modal -->
  <div x-show="showSignup" x-cloak class="fixed inset-0 bg-slate-900/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
    <div class="bg-white rounded-2xl max-w-md w-full p-8 shadow-2xl relative" @click.away="showSignup = false">
      <button @click="showSignup = false" class="absolute top-4 right-4 text-gray-400 hover:text-gray-700"><i data-lucide="x" class="w-6 h-6"></i></button>
      
      <div x-show="!success">
        <h2 class="text-2xl font-bold text-slate-900 mb-2">Create your account</h2>
        <p class="text-gray-500 text-sm mb-6">Join hundreds of shops modernizing their operations. Start your 14-day free trial.</p>
        
        <form @submit.prevent="submitSignup()" class="space-y-4">
          <div>
            <label class="block text-sm font-medium mb-1">Business Name</label>
            <input type="text" x-model="form.business_name" class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" required>
          </div>
          <div>
            <label class="block text-sm font-medium mb-1">Your Name</label>
            <input type="text" x-model="form.contact_name" class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" required>
          </div>
          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="block text-sm font-medium mb-1">Email</label>
              <input type="email" x-model="form.contact_email" class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" required>
            </div>
            <div>
              <label class="block text-sm font-medium mb-1">Phone</label>
              <input type="tel" x-model="form.contact_phone" class="w-full px-4 py-2 border rounded-lg focus:ring-2 focus:ring-indigo-500 outline-none" required>
            </div>
          </div>
          <div class="flex items-start gap-2 pt-2">
            <input type="checkbox" required class="mt-1">
            <label class="text-xs text-gray-500 leading-tight">I agree to the <a href="/terms" target="_blank" class="text-indigo-600 hover:underline">Terms of Service</a> and Privacy Policy.</label>
          </div>
          <button type="submit" class="w-full bg-indigo-600 text-white py-3 rounded-lg font-bold hover:bg-indigo-700 transition" :disabled="loading">
            <span x-text="loading ? 'Submitting...' : 'Submit Application'"></span>
          </button>
        </form>
      </div>

      <div x-show="success" class="text-center py-8">
        <div class="w-16 h-16 bg-green-100 text-green-600 rounded-full flex items-center justify-center mx-auto mb-4">
          <i data-lucide="check" class="w-8 h-8"></i>
        </div>
        <h2 class="text-2xl font-bold text-slate-900 mb-2">Application Received!</h2>
        <p class="text-gray-500 text-sm mb-6">Thank you! Our onboarding team will review your business details and send your login credentials via email within 24 hours.</p>
        <button @click="showSignup = false" class="bg-slate-100 text-slate-700 px-6 py-2 rounded-lg font-medium hover:bg-slate-200">Close</button>
      </div>
    </div>
  </div>

  <script>
    function landingApp() {
      return {
        showSignup: false,
        loading: false,
        success: false,
        form: { business_name: '', contact_name: '', contact_email: '', contact_phone: '' },
        async submitSignup() {
          this.loading = true;
          try {
            // We post to the existing SaaS signup endpoint
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
print("✅ Created landing.html with modern UI and onboarding modal")

print("\n🎉 Landing Page Complete! Restart your server and go to http://localhost:8000")