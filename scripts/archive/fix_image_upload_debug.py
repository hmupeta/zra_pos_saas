import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Add verbose logging to backend PUT request
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Regex to replace the PUT block
new_put_block = '''    elif request.method == 'PUT':
        data = request.data
        product_id = data.get("id")
        if not product_id:
             return Response({"error": "Product ID required"}, status=400)
             
        print("\\n--- DIAGNOSTIC: PUT Product Request ---")
        print("Request.FILES:", request.FILES)
        print("Request.data keys:", list(request.data.keys()))
             
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
                print("✅ Image found in request.FILES:", p.image.name)
            elif "image" in request.data and hasattr(request.data["image"], "read"):
                p.image = request.data["image"]
                print("✅ Image found in request.data:", p.image.name)
            else:
                print("⚠️ NO image found in request. Existing image preserved.")
                
            p.save()
            print("✅ Saved product. Has image?", bool(p.image))
            
            return Response({"success": True, "id": p.id, "has_image": bool(p.image)})
            
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)
        except Exception as e:
             import traceback
             print(traceback.format_exc())
             return Response({"error": str(e)}, status=400)'''

pattern = r"    elif request\.method == 'PUT':.*?return Response\(\{\"error\": str\(e\)\}, status=400\)"
if re.search(pattern, v_content, flags=re.DOTALL):
    v_content = re.sub(pattern, new_put_block, v_content, flags=re.DOTALL)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Backend updated with verbose logging.")
else:
    print("⚠️ Could not find PUT block. Manual check needed.")

# ============================================================
# 2. Verify Media Directory exists
# ============================================================
media_dir = BACKEND_PATH / "media" / "products"
media_dir.mkdir(parents=True, exist_ok=True)
print(f"✅ Ensured media directory exists: {media_dir}")

# ============================================================
# 3. Force check on Frontend api.js to ensure FormData works
# ============================================================
api_js = BACKEND_PATH / "static" / "pos" / "api.js"
js_content = api_js.read_text(encoding="utf-8")

# Ensure headers don't override Content-Type for FormData
if "const isFormData = options.body instanceof FormData;" not in js_content:
    print("⚠️ api.js is missing FormData detection. Adding it...")
    js_content = js_content.replace(
        "const headers = { 'Content-Type': 'application/json', ...(options.headers || {}) };",
        """const isFormData = options.body instanceof FormData;
  const headers = { 
    ...(isFormData ? {} : { 'Content-Type': 'application/json' }), 
    ...(options.headers || {}) 
  };"""
    )
    api_js.write_text(js_content, encoding="utf-8")
    print("✅ Fixed api.js")
else:
    print("✅ api.js correctly handles FormData.")

print("\n🎉 Done! Restart the server.")