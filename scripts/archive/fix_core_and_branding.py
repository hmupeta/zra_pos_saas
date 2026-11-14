import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Rebuild core/views.py completely to remove corruption
# ============================================================
core_views_path = BACKEND_PATH / "core" / "views.py"
new_views = '''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate, get_user_model
from django.db import transaction
from .models import User, Company, BranchAccess
from .serializers import UserSerializer

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    username = request.data.get("username")
    password = request.data.get("password")
    user = authenticate(request, username=username, password=password)
    if not user:
        return Response({"error": "Invalid credentials"}, status=401)
    if user.employment_status != "ACTIVE":
        return Response({"error": f"Account is {user.employment_status}"}, status=403)
    if user.is_locked():
        return Response({"error": "Account locked. Try again later."}, status=403)
    
    token, _ = Token.objects.get_or_create(user=user)
    return Response({
        "token": token.key,
        "user": UserSerializer(user).data,
        "tenant": user.tenant.name if user.tenant else None,
        "tenant_code": user.tenant.code if user.tenant else None,
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        request.user.auth_token.delete()
    except Exception:
        pass
    return Response({"message": "Logged out"})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request):
    return Response(UserSerializer(request.user).data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def branches_list(request):
    qs = BranchAccess.objects.filter(user=request.user, company__is_active=True).select_related("company")
    return Response([{
        "id": ba.company.id, 
        "name": ba.company.name, 
        "code": ba.company.branch_code, 
        "tpin": ba.company.tpin,
        "is_current": False 
    } for ba in qs])

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def switch_branch(request):
    branch_id = request.data.get("branch_id")
    try:
        branch = Company.objects.get(pk=branch_id, tenant=request.user.tenant)
    except Company.DoesNotExist:
        return Response({"error": "Branch not found"}, status=404)
        
    has_access = request.user.branch_access.filter(company=branch).exists()
    if not has_access and request.user.user_type not in ("SUPER_ADMIN", "TENANT_OWNER", "ADMIN"):
        return Response({"error": "No access to this branch"}, status=403)
        
    request.session["branch_id"] = branch.id
    return Response({"success": True, "branch_id": branch.id, "branch_name": branch.name})

@api_view(["GET"])
@permission_classes([AllowAny])
def health(request):
    return Response({"status": "ok"})

# --- User Management ---
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def users_list_create(request):
    if request.user.user_type != "TENANT_OWNER":
        return Response({"error": "Only Tenant Admins can manage users"}, status=403)

    if request.method == "GET":
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

    if User.objects.filter(username=username).exists():
        return Response({"error": "Username already exists"}, status=400)

    try:
        with transaction.atomic():
            user = User.objects.create_user(
                username=username, email=email, password=password,
                tenant=request.tenant, user_type=role, employment_status="ACTIVE"
            )
            if request.branch:
                BranchAccess.objects.create(user=user, company=request.branch, is_default=True)
            return Response({"success": True, "id": user.id}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

# --- Company Settings & Branding ---
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def company_settings(request):
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Only Admins can change settings"}, status=403)
    
    branch = request.branch
    if not branch:
        return Response({"error": "No active branch. Please select a branch."}, status=400)

    if request.method == "GET":
        return Response({
            "name": branch.name,
            "tpin": branch.tpin,
            "address": branch.address,
            "phone": branch.phone,
            "email": branch.email,
            "logo_url": branch.logo.url if branch.logo else None,
        })

    # POST (Handle Multipart for Logo Upload)
    branch.name = request.data.get("name", branch.name)
    branch.tpin = request.data.get("tpin", branch.tpin)
    branch.address = request.data.get("address", branch.address)
    branch.phone = request.data.get("phone", branch.phone)
    branch.email = request.data.get("email", branch.email)

    if "logo" in request.FILES:
        branch.logo = request.FILES["logo"]

    branch.save()
    return Response({"success": True, "message": "Settings updated"})
'''
core_views_path.write_text(new_views.strip(), encoding="utf-8")
print("✅ Rebuilt core/views.py (Fixed Imports)")

# ============================================================
# 2. Rebuild core/urls.py
# ============================================================
core_urls_path = BACKEND_PATH / "core" / "urls.py"
new_urls = '''
from django.urls import path
from . import views

urlpatterns = [
    path("login/", views.login, name="login"),
    path("logout/", views.logout, name="logout"),
    path("me/", views.me, name="me"),
    path("branches/", views.branches_list, name="branches_list"),
    path("branches/switch/", views.switch_branch, name="switch_branch"),
    path("health/", views.health, name="health"),
    path("users/", views.users_list_create, name="users_list_create"),
    path("company/", views.company_settings, name="company_settings"),
]
'''
core_urls_path.write_text(new_urls.strip(), encoding="utf-8")
print("✅ Rebuilt core/urls.py")

# ============================================================
# 3. Fix api.js to handle non-JSON server errors
# ============================================================
api_js = BACKEND_PATH / "static" / "pos" / "api.js"
js_content = api_js.read_text(encoding="utf-8")

old_parse = """
  const text = await res.text();
  const data = text ? JSON.parse(text) : null;
  if (!res.ok) {
    const err = new Error((data && data.error) || `HTTP ${res.status}`);
    err.response = { status: res.status, data };
    throw err;
  }
  return data;
"""

new_parse = """
  const text = await res.text();
  let data = null;
  
  if (text) {
    try {
      data = JSON.parse(text);
    } catch (e) {
      console.error("Non-JSON response received:", text.substring(0, 200));
      if (!res.ok) throw new Error(`Server Error (${res.status}). Check terminal console.`);
      return text;
    }
  }

  if (!res.ok) {
    const err = new Error((data && data.error) || `HTTP ${res.status}`);
    err.response = { status: res.status, data };
    throw err;
  }
  return data;
"""
js_content = js_content.replace(old_parse, new_parse)
api_js.write_text(js_content, encoding="utf-8")
print("✅ Fixed api.js to prevent JSON.parse crashes")

# ============================================================
# 4. Recreate Settings UI (Branding & Logo)
# ============================================================
settings_html = BACKEND_PATH / "templates" / "pos" / "settings.html"
new_settings = '''
{% extends "pos/base.html" %}
{% block title %}Shop Settings{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="settingsPage()" x-init="load()">
    <h1 class="text-2xl font-bold mb-6">Shop Settings & Branding</h1>

    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      
      <!-- Branding Form -->
      <div class="card p-6">
        <h2 class="font-semibold mb-4 text-lg">Company Details</h2>
        <form @submit.prevent="save()" class="space-y-4">
          <div>
            <label class="block text-sm mb-1">Shop/Branch Name</label>
            <input type="text" x-model="form.name" class="input-field" required>
          </div>
          <div>
            <label class="block text-sm mb-1">TPIN</label>
            <input type="text" x-model="form.tpin" class="input-field">
          </div>
          <div>
            <label class="block text-sm mb-1">Phone</label>
            <input type="text" x-model="form.phone" class="input-field">
          </div>
          <div>
            <label class="block text-sm mb-1">Email</label>
            <input type="email" x-model="form.email" class="input-field">
          </div>
          <div>
            <label class="block text-sm mb-1">Address (Printed on Receipt)</label>
            <textarea x-model="form.address" class="input-field" rows="2"></textarea>
          </div>
          
          <div class="border-t pt-4 mt-4">
            <label class="block text-sm font-medium mb-2">Shop Logo</label>
            <p class="text-xs text-gray-500 mb-2">Appears on receipts and as a watermark.</p>
            <input type="file" @change="handleFile" accept="image/*" class="block w-full text-sm text-gray-500 file:mr-4 file:py-2 file:px-4 file:rounded file:border-0 file:text-sm file:font-semibold file:bg-brand-50 file:text-brand-700 hover:file:bg-brand-100">
          </div>

          <button type="submit" class="btn-primary w-full mt-4" :disabled="saving">
            <span x-show="!saving">Save Settings</span>
            <span x-show="saving">Saving...</span>
          </button>
        </form>
      </div>

      <!-- Logo Preview -->
      <div class="card p-6 flex flex-col items-center justify-center bg-gray-50">
        <h2 class="font-semibold mb-4 text-gray-500">Current Logo</h2>
        <template x-if="previewUrl || form.logo_url">
          <img :src="previewUrl || form.logo_url" class="max-w-xs max-h-64 object-contain bg-white p-4 shadow-sm border rounded-lg" alt="Shop Logo">
        </template>
        <template x-if="!previewUrl && !form.logo_url">
          <div class="text-gray-400 text-sm">No logo uploaded yet.</div>
        </template>
      </div>

    </div>

    <div class="card p-6 mt-6">
      <h2 class="font-semibold mb-4">Payment Gateways (this branch)</h2>
      <div class="space-y-2">
        <template x-for="c in configs" :key="c.id">
          <div class="flex justify-between items-center p-3 bg-gray-50 rounded-lg">
            <div>
              <div class="font-medium" x-text="c.provider"></div>
              <div class="text-xs text-gray-500">Merchant: <span x-text="c.merchant_id || '-'"></span></div>
            </div>
          </div>
        </template>
        <div x-show="configs.length === 0" class="text-sm text-gray-400">No payment gateways configured.</div>
      </div>
    </div>

  </div>
</div>
<script>
function settingsPage() {
  return {
    form: { name: '', tpin: '', address: '', phone: '', email: '', logo_url: null },
    configs: [],
    saving: false,
    previewUrl: null,
    logoFile: null,

    async load() {
      if (!requireAuth() || !requireBranch()) return;
      try { 
        this.form = await apiFetch('/auth/company/');
        this.configs = await apiFetch('/payments/configs/');
      } catch (e) { alert(e.message); }
    },

    handleFile(e) {
      const file = e.target.files[0];
      if (file) {
        this.logoFile = file;
        this.previewUrl = URL.createObjectURL(file);
      }
    },

    async save() {
      this.saving = true;
      try {
        const fd = new FormData();
        fd.append('name', this.form.name);
        fd.append('tpin', this.form.tpin);
        fd.append('address', this.form.address);
        fd.append('phone', this.form.phone);
        fd.append('email', this.form.email);
        if (this.logoFile) fd.append('logo', this.logoFile);

        // Custom fetch for FormData to ensure Auth header is set correctly
        const token = getToken();
        const res = await fetch('/api/auth/company/', {
          method: 'POST',
          headers: { 'Authorization': `Token ${token}` }, // Do NOT set Content-Type
          body: fd
        });
        
        if (!res.ok) {
           const errData = await res.json().catch(() => ({}));
           throw new Error(errData.error || 'Failed to update');
        }
        
        alert('Settings updated successfully!');
        this.logoFile = null;
        this.previewUrl = null;
        this.load(); // Reload to show saved image
      } catch (e) {
        alert('Failed to update settings: ' + e.message);
      } finally {
        this.saving = false;
      }
    }
  }
}
</script>
{% endblock %}
'''
settings_html.write_text(new_settings.strip(), encoding="utf-8")
print("✅ Recreated Settings UI with Branding")

print("\n🎉 Fix Complete! Run 'python manage.py runserver'")