from django.db import models
from tenants.models import Company

class Plan(models.Model):
    name = models.CharField(max_length=50) # Basic, Professional, Enterprise
    price_zmw = models.DecimalField(max_digits=10, decimal_places=2)
    
    # Limits: Use -1 to represent "Unlimited"
    max_branches = models.IntegerField(default=1) 
    max_users = models.IntegerField(default=5)
    
    # Feature Flags
    has_api_access = models.BooleanField(default=False)
    has_multi_branch_reports = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name

class Subscription(models.Model):
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='subscription')
    plan = models.ForeignKey(Plan, on_delete=models.PROTECT)
    is_active = models.BooleanField(default=True)
    started_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.company.name} - {self.plan.name}"

class TenantUsage(models.Model):
    """Tracks current usage to avoid expensive COUNT(*) queries on every API call."""
    company = models.OneToOneField(Company, on_delete=models.CASCADE, related_name='usage')
    current_branches = models.IntegerField(default=0)
    current_users = models.IntegerField(default=0)
    last_updated = models.DateTimeField(auto_now=True)
