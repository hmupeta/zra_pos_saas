"""Barcode cache service."""
from django.core.cache import cache
from .models import Product

PREFIX = "bc:"


class BarcodeService:
    @staticmethod
    def lookup(tenant_id, company_id, barcode):
        if not barcode:
            return None
        key = f"{PREFIX}{tenant_id}:{company_id}:{barcode}"
        cached = cache.get(key)
        if cached is not None:
            return None if cached == "__NULL__" else cached
        p = Product.objects.filter(
            tenant_id=tenant_id, company_id=company_id,
            barcode=barcode, is_active=True,
        ).first()
        if not p:
            cache.set(key, "__NULL__", 300)
            return None
        data = {
            "id": p.id, "barcode": p.barcode, "name": p.name,
            "selling_price": float(p.selling_price),
            "current_stock": float(p.current_stock),
            "tax_rate": float(p.tax_rate.rate),
            "tax_type": p.tax_rate.tax_type,
            "zra_item_code": p.zra_item_code or p.category.zra_item_code,
        }
        cache.set(key, data, 3600)
        return data

    @staticmethod
    def invalidate(tenant_id, company_id, barcode):
        cache.delete(f"{PREFIX}{tenant_id}:{company_id}:{barcode}")
