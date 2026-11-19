import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model
from inventory.models import Product
from core.models import Company

print("="*50)
print("1. CHECKING DATABASE & DISK")
print("="*50)
p = Product.objects.exclude(image='').exclude(image__isnull=True).first()
if not p:
    print("❌ CRITICAL: No products have an image saved in the database.")
    print("   You need to re-upload the images via the UI.")
else:
    print(f"Product: {p.name}")
    print(f"DB Image Field: {p.image}")
    
    # Check if file exists on disk
    file_path = p.image.path
    if os.path.exists(file_path):
        print(f"✅ File exists on disk at: {file_path}")
    else:
        print(f"❌ CRITICAL: File NOT found on disk at: {file_path}")

    print(f"API Image URL: {p.image.url}")

print("\n" + "="*50)
print("2. CHECKING API RESPONSE")
print("="*50)
User = get_user_model()
cashier = User.objects.get(username='cashier1')
client = APIClient()
client.force_authenticate(user=cashier)

# We must simulate the branch header
branch = Company.objects.first()
response = client.get('/api/inventory/products/', HTTP_X_BRANCH_ID=str(branch.id))

print(f"Status Code: {response.status_code}")
if response.status_code == 200:
    products = response.data
    if isinstance(products, list):
        found_image = False
        for prod in products:
            if prod.get('image_url'):
                print(f"✅ API IS SENDING: {prod['name']} -> {prod['image_url']}")
                found_image = True
                break
        if not found_image:
            print("❌ CRITICAL: The API response does NOT contain 'image_url' for any product.")
            print("   Response data sample:", products[0] if products else "Empty List")
    else:
        print("❌ API returned unexpected format:", products)
else:
    print(f"❌ API Error: {response.data}")