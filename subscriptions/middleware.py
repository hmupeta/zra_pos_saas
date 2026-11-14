from subscriptions.models import Subscription, TenantUsage

class TenantLimitMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # We check if the user has a 'company' attribute (you will need to add this to your core.User model)
        if request.user.is_authenticated and hasattr(request.user, 'company') and request.user.company:
            try:
                subscription = Subscription.objects.select_related('plan').get(company=request.user.company)
                usage, _ = TenantUsage.objects.get_or_create(company=request.user.company)
                request.tenant_plan = subscription.plan
                request.tenant_usage = usage
            except Subscription.DoesNotExist:
                request.tenant_plan = None
                request.tenant_usage = None
        return self.get_response(request)
