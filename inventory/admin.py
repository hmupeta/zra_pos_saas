from django.contrib import admin
from .models import Product, Category, TaxRate, StockMovement


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("barcode", "name", "selling_price", "current_stock", "tenant", "company")
    list_filter = ("tenant", "company", "is_active")


admin.site.register(Category)
admin.site.register(TaxRate)
admin.site.register(StockMovement)
