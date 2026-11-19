import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

# --- ALLOW testserver for the APIClient ---
from django.conf import settings
if "testserver" not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ["testserver"]

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from core.models import Company
from inventory.models import Product

User = get_user_model()
cashier = User.objects.get(username='cashier1')
branch = Company.objects.first()

print("--- DB CHECK ---")
print(f"Branch: {branch.name} (ID: {branch.id})")
print(f"Products in DB for this branch: {Product.objects.filter(company=branch).count()}")

print("\n--- API SIMULATION ---")
client = APIClient()
client.force_authenticate(user=cashier)

response = client.get('/api/inventory/products/', HTTP_X_BRANCH_ID=str(branch.id))

print(f"Status Code: {response.status_code}")

# Handle both JSON and plain responses
if hasattr(response, 'data') and isinstance(response.data, list):
    print(f"Products returned by API: {len(response.data)}")
    if len(response.data) > 0:
        print(f"Success! First product: {response.data[0]['name']}")
    else:
        print("Empty Response (API is filtering out the products)")
else:
    print(f"Unexpected response: {response.content[:200]}")