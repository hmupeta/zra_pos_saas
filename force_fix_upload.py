import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "inventory" / "views.py"

content = views_path.read_text(encoding="utf-8")

# The exact, bulletproof replacement for the PUT block
new_put_block = '''    elif request.method == 'PUT':
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
            
            # Robust Image Handling
            if "image" in request.FILES:
                p.image = request.FILES["image"]
            elif "image" in request.data and hasattr(request.data["image"], "read"):
                p.image = request.data["image"]
                
            p.save()
            
            # NOTE: We do not return the URL here because Django holds the file in memory
            # The frontend automatically reloads the list to fetch the real URL
            return Response({"success": True, "id": p.id})
            
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)
        except Exception as e:
             import traceback
             print(traceback.format_exc())
             return Response({"error": str(e)}, status=400)'''

# Regex to find the entire PUT block within products_list and replace it
pattern = r"    elif request\.method == 'PUT':.*?return Response\(\{\"error\": str\(e\)\}, status=400\)"

if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_put_block, content, flags=re.DOTALL)
    views_path.write_text(content, encoding="utf-8")
    print("✅ Forcefully replaced the PUT block in inventory/views.py.")
else:
    print("⚠️ Regex failed. Attempting to insert a clean PUT block via targeted string replacement.")
    # If the above fails, we just remove the exact line that's crashing
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if '"image_url": p.image.url if p.image else None' in line and 'return Response({"success": True' in line:
            lines[i] = '            return Response({"success": True, "id": p.id})'
            print("✅ Removed the specific crashing line.")
            break
    views_path.write_text('\n'.join(lines), encoding="utf-8")

print("\n🎉 Done! Restart the server and test the image upload.")