import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "inventory" / "views.py"

content = views_path.read_text(encoding="utf-8")

# The perfect, error-free products_list view
new_view = '''
@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])
def products_list(request):
    if request.method == 'GET':
        product_id = request.query_params.get('id')
        if product_id:
            try:
                p = Product.objects.get(id=product_id, tenant=request.tenant)
                return Response({
                    "id": p.id, "barcode": p.barcode, "name": p.name,
                    "category_id": p.category_id, "tax_rate_id": p.tax_rate_id,
                    "unit_cost": float(p.unit_cost), "selling_price": float(p.selling_price),
                    "discount_percentage": float(p.discount_percentage),
                    "current_stock": float(p.current_stock), "reorder_level": float(p.reorder_level),
                    "image_url": p.image.url if p.image else None,
                })
            except Product.DoesNotExist:
                return Response({"error": "Product not found"}, status=404)

        search = request.query_params.get('search', '')
        products = Product.objects.filter(tenant=request.tenant, company=request.branch, is_active=True)
        if search:
            products = products.filter(name__icontains=search) | products.filter(barcode__icontains=search)
            
        data = []
        for p in products:
            data.append({
                "id": p.id,
                "barcode": p.barcode,
                "name": p.name,
                "selling_price": float(p.selling_price),
                "discount_percentage": float(p.discount_percentage),
                "unit_cost": float(p.unit_cost),
                "current_stock": float(p.current_stock),
                "tax_rate": float(p.tax_rate.rate),
                "category_name": p.category.name,
                "image_url": p.image.url if p.image else None,
            })
        return Response(data)
        
    elif request.method == 'PUT':
        data = request.data
        product_id = data.get("id")
        if not product_id:
             return Response({"error": "Product ID required"}, status=400)
             
        try:
            p = Product.objects.get(id=product_id, tenant=request.tenant)
            p.name = data.get("name", p.name)
            p.barcode = data.get("barcode", p.barcode)
            p.category_id = data.get("category_id", p.category_id)
            p.tax_rate_id = data.get("tax_rate_id", p.tax_rate_id)
            p.unit_cost = Decimal(str(data.get("unit_cost", p.unit_cost)))
            p.selling_price = Decimal(str(data.get("selling_price", p.selling_price)))
            p.discount_percentage = Decimal(str(data.get("discount_percentage", p.discount_percentage)))
            p.reorder_level = Decimal(str(data.get("reorder_level", p.reorder_level)))
            
            # Handle Image Upload
            if "image" in request.FILES:
                p.image = request.FILES["image"]
            elif "image" in request.data and hasattr(request.data["image"], "read"):
                p.image = request.data["image"]
                
            p.save()
            
            # Return safe response (no image.url access here to avoid InMemoryUploadedFile crash)
            return Response({"success": True, "id": p.id, "has_image": bool(p.image)})
            
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)
        except Exception as e:
             return Response({"error": str(e)}, status=400)

    # POST: Create Product
    data = request.data
    try:
        barcode = data.get("barcode") or str(uuid.uuid4().hex[:10]).upper()
        
        product = Product.objects.create(
            tenant=request.tenant,
            company=request.branch,
            barcode=barcode,
            name=data.get("name"),
            description=data.get("description", ""),
            category_id=data.get("category_id"),
            tax_rate_id=data.get("tax_rate_id"),
            unit_cost=Decimal(str(data.get("unit_cost", 0))),
            selling_price=Decimal(str(data.get("selling_price", 0))),
            discount_percentage=Decimal(str(data.get("discount_percentage", 0))),
            current_stock=Decimal(str(data.get("current_stock", 0))),
            reorder_level=Decimal(str(data.get("reorder_level", 10))),
            zra_item_code=data.get("zra_item_code", ""),
            image=request.FILES.get("image")
        )
        return Response({"success": True, "id": product.id}, status=201)
    except Exception as e:
        return Response({"error": str(e)}, status=400)
'''

# Replace the entire products_list function
pattern = r"@api_view\(\['GET', 'POST', 'PUT'\]\).*?def products_list\(request\):.*?return Response\(\{\"error\": str\(e\)\}, status=400\)"

if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_view.strip(), content, flags=re.DOTALL)
    views_path.write_text(content, encoding="utf-8")
    print("✅ Successfully rebuilt products_list view with no syntax errors.")
else:
    print("⚠️ Regex failed. The file might be badly corrupted. Please check inventory/views.py manually around line 68.")

print("\n🎉 Done! Restart the server.")