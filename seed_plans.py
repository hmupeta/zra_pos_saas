import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from subscriptions.models import Plan

plans = [
    {"name": "Basic", "price_zmw": 500, "max_branches": 1, "max_users": 5, "has_api_access": False},
    {"name": "Professional", "price_zmw": 1500, "max_branches": 5, "max_users": 25, "has_api_access": True},
    {"name": "Enterprise", "price_zmw": 0, "max_branches": -1, "max_users": -1, "has_api_access": True},
]

for p in plans:
    obj, created = Plan.objects.get_or_create(name=p["name"], defaults=p)
    if created:
        print(f"✅ Seeded Plan: {p['name']}")
    else:
        print(f"ℹ️  Plan already exists: {p['name']}")