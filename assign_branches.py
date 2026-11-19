import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Company, BranchAccess

def main():
    print("Assigning BranchAccess to users...")
    User = get_user_model()
    
    branch = Company.objects.filter(name__icontains='Demo').first()
    if not branch:
        branch = Company.objects.first()
        
    if not branch:
        print("ERROR: Could not find any branch to assign.")
        return

    for uname in ['cashier1', 'manager1', 'accountant1', 'finance1']:
        try:
            u = User.objects.get(username=uname)
            BranchAccess.objects.get_or_create(user=u, company=branch)
            print(f"SUCCESS: Assigned {uname} to {branch.name}")
        except User.DoesNotExist:
            print(f"SKIP: User {uname} does not exist.")

if __name__ == "__main__":
    main()