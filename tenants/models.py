import uuid
from django.db import models

class Company(models.Model):
    """The Tenant. Represents a single business entity paying for a subscription."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    tpin = models.CharField(max_length=10, unique=True, help_text="ZRA Taxpayer Identification Number")
    parent_company = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='subsidiaries')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Branch(models.Model):
    """A physical location of the Company. Limited by the subscription plan."""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    company = models.ForeignKey(Company, on_delete=models.CASCADE, related_name='branches')
    name = models.CharField(max_length=255)
    branch_code = models.CharField(max_length=10)
    address = models.TextField(blank=True)
    is_active = models.BooleanField(default=True) # Used for downgrades

    class Meta:
        unique_together = ('company', 'branch_code')

    def __str__(self):
        return f"{self.company.name} - {self.name}"
