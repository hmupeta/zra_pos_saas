from django.http import JsonResponse
from core.models import BranchAccess

class StrictBranchMiddleware:
    """Forces Cashiers and Managers to only access their assigned branch."""
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
    """Blocks Platform Admins from accessing tenant POS data."""
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated and request.user.user_type == 'PLATFORM_ADMIN':
            tenant_api_paths = ['/api/inventory/', '/api/sales/', '/api/customers/', '/api/payments/', '/api/pos/']
            if any(request.path.startswith(path) for path in tenant_api_paths):
                return JsonResponse({"error": "Platform Admins do not have access to tenant store data."}, status=403)
        return self.get_response(request)
