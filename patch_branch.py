import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Company

User = get_user_model()

def run():
    print("Starting branch patch...")
    company = Company.objects.first()
    if not company:
        print("No company found in DB!")
        return

    print(f"Found Company: {company.name} (ID: {company.id})")

    users = User.objects.all()
    for u in users:
        u.company = company
        u.save()
        print(f"Assigned user {u.username} to {company.name}")
        
    print("Patch complete!")

if __name__ == "__main__":
    run()
