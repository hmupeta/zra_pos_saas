import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.conf import settings
if 'testserver' not in settings.ALLOWED_HOSTS:
    settings.ALLOWED_HOSTS = list(settings.ALLOWED_HOSTS) + ['testserver']

from rest_framework.test import APIClient
from django.contrib.auth import get_user_model

User = get_user_model()
cashier = User.objects.get(username='cashier1')
client = APIClient()
client.force_authenticate(user=cashier)

response = client.get('/api/inventory/products/')

found = False
for p in response.data:
    if p.get('image_url'):
        print(f"PRODUCT: {p['name']}")
        print(f"IMAGE URL: {p['image_url']}")
        found = True

if not found:
    print("❌ No products returned an image_url. The backend is NOT sending images.")
else:
    print("✅ The backend IS sending image URLs correctly.")