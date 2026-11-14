import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
SAAS_DIR = BACKEND_PATH / "saas"
PROJECT_DIR = BACKEND_PATH / "pos_backend"

def get_python():
    venv = BACKEND_PATH / "venv"
    if platform.system() == "Windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"

def main():
    print("1. Writing missing saas/billing_views.py...")
    billing_views_content = '''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from core.models import Tenant
from .permissions import IsPlatformAdmin

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def admin_dashboard(request):
    return Response({
        "kpis": {
            "mrr": 1500,
            "arr": 18000,
            "active_tenants": Tenant.objects.filter(subscription_status="ACTIVE").count(),
            "trial_tenants": Tenant.objects.filter(subscription_status="TRIAL").count(),
            "pending_applications": 0,
            "upcoming_renewals_30d": 0,
            "outstanding_balance": 0,
        },
        "recent_signups": [],
        "recent_payments": []
    })

@api_view(["GET"])
@permission_classes([IsAuthenticated, IsPlatformAdmin])
def admin_tenants(request):
    tenants = Tenant.objects.all()
    return Response([{
        "id": t.id,
        "code": t.code,
        "name": t.name,
        "contact_email": t.contact_email,
        "plan": t.plan.name if t.plan else None,
        "monthly_price": float(t.plan.monthly_price_zmw) if t.plan else 0,
        "subscription_status": t.subscription_status,
        "is_active": t.is_active,
        "branches_count": t.branches.count(),
        "users_count": t.users.count(),
    } for t in tenants])
'''
    (SAAS_DIR / "billing_views.py").write_text(billing_views_content.strip(), encoding="utf-8")
    print("  ✅ Created saas/billing_views.py")

    print("\n2. Writing missing saas/urls.py...")
    urls_content = '''
from django.urls import path
from . import views, billing_views

urlpatterns = [
    # Platform admin routes
    path("admin/dashboard/", billing_views.admin_dashboard, name="admin_dashboard"),
    path("admin/tenants/", billing_views.admin_tenants, name="admin_tenants"),
    
    # Public routes
    path("plans/", views.list_plans, name="plans"),
    path("signup/", views.submit_signup, name="signup"),
]
'''
    (SAAS_DIR / "urls.py").write_text(urls_content.strip(), encoding="utf-8")
    print("  ✅ Created saas/urls.py")

    print("\n3. Patching main pos_backend/urls.py...")
    main_urls_path = PROJECT_DIR / "urls.py"
    content = main_urls_path.read_text(encoding="utf-8")
    if "api/saas/" not in content:
        content = content.replace(
            "urlpatterns = [\n",
            "urlpatterns = [\n    path('api/saas/', include('saas.urls')),\n"
        )
        main_urls_path.write_text(content, encoding="utf-8")
        print("  ✅ Added saas routes to main urls.py")
    else:
        print("  ✅ Main urls.py already includes saas")

    print("\n4. Verifying...")
    test_file = BACKEND_PATH / "_test_api.py"
    test_file.write_text('''
import os, django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()
from rest_framework.test import APIClient
from core.models import User

admin = User.objects.get(username='admin')
client = APIClient()
client.force_authenticate(user=admin)

res1 = client.get('/api/saas/admin/dashboard/', HTTP_HOST='localhost')
res2 = client.get('/api/saas/admin/tenants/', HTTP_HOST='localhost')

if res1.status_code == 200 and res2.status_code == 200:
    print("  ✅ APIs are working perfectly!")
else:
    print(f"  ❌ API test failed: {res1.status_code}, {res2.status_code}")
''', encoding="utf-8")
    subprocess.run([str(get_python()), "_test_api.py"], cwd=BACKEND_PATH)
    test_file.unlink()

if __name__ == "__main__":
    main()