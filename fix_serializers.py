import os
import subprocess
import platform
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Create inventory/serializers.py
# ============================================================
serializers_code = '''
from rest_framework import serializers
from .models import Product, Category, TaxRate

class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'

class TaxRateSerializer(serializers.ModelSerializer):
    class Meta:
        model = TaxRate
        fields = '__all__'

class ProductSerializer(serializers.ModelSerializer):
    category_name = serializers.CharField(source='category.name', read_only=True)
    tax_rate_value = serializers.FloatField(source='tax_rate.rate', read_only=True)
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = Product
        fields = '__all__'

    def get_image_url(self, obj):
        return obj.image.url if obj.image else None
'''
(Path(BACKEND_PATH) / "inventory" / "serializers.py").write_text(serializers_code.strip(), encoding="utf-8")
print("✅ Created inventory/serializers.py")

# ============================================================
# 2. Run Migrations
# ============================================================
print("Running migrations...")
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "inventory"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)

print("\n🎉 Done! You can now run 'python manage.py runserver'.")