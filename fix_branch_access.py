import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Company, BranchAccess

User = get_user_model()

def run():
    print("Starting BranchAccess patch...")
    
    company = Company.objects.filter(branch_code="HQ").first()
    if not company:
        print("No company found!")
        return

    users = User.objects.filter(username__in=['admin', 'demo_owner'])
    
    for u in users:
        access, created = BranchAccess.objects.get_or_create(
            user=u,
            company=company
        )
        if created:
            print(f"Granted BranchAccess to {u.username} for {company.name}")
        else:
            print(f"{u.username} already has access.")

    print("BranchAccess Patch complete!")

if __name__ == "__main__":
    run()