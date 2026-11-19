import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from inventory.models import Product
from django.db.models import Count

def main():
    # Find all duplicate barcodes
    dupes = Product.objects.values('barcode').annotate(count=Count('id')).filter(count__gt=1)
    print(f"Found {len(dupes)} duplicate barcodes\n")
    
    for d in dupes:
        barcode = d['barcode']
        products = Product.objects.filter(barcode=barcode).order_by('-image', 'id')
        
        # Keep the one with an image (or the oldest if none have images)
        keep = products.filter(image__isnull=False).exclude(image='').first()
        if not keep:
            keep = products.first()
        
        # Delete the rest
        to_delete = products.exclude(pk=keep.pk)
        delete_count = to_delete.count()
        names = [f"{p.name} (img: {bool(p.image)})" for p in to_delete]
        to_delete.delete()
        
        print(f"  {barcode}: kept '{keep.name}' (img: {bool(keep.image)}), deleted {delete_count} duplicates")
        for n in names:
            print(f"    - deleted: {n}")
    
    print(f"\n✅ Cleanup complete")
    print(f"   Total products now: {Product.objects.count()}")
    
    # Verify
    print("\nRemaining products with target barcodes:")
    for p in Product.objects.filter(barcode__in=['COKE500', 'FANTA500', 'BREAD01', 'SPRITE500']):
        print(f"   {p.barcode} | {p.name} | Image: {bool(p.image)}")

if __name__ == "__main__":
    main()