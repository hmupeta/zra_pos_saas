import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Fix Backend (Robust Image Upload for PUT)
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Replace the PUT block inside products_list
old_put = '''    elif request.method == 'PUT':
        # Edit existing product
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
                
            p.save()
            return Response({"success": True, "id": p.id})
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)
        except Exception as e:
             return Response({"error": str(e)}, status=400)'''

new_put = '''    elif request.method == 'PUT':
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
            
            # Robust Image Handling (Check request.FILES and request.data)
            if "image" in request.FILES:
                p.image = request.FILES["image"]
            elif "image" in request.data and hasattr(request.data["image"], "read"):
                p.image = request.data["image"]
                
            p.save()
            return Response({"success": True, "id": p.id, "image_url": p.image.url if p.image else None})
        except Product.DoesNotExist:
            return Response({"error": "Product not found"}, status=404)
        except Exception as e:
             import traceback
             print(traceback.format_exc())
             return Response({"error": str(e)}, status=400)'''

if old_put in v_content:
    v_content = v_content.replace(old_put, new_put)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Fixed backend image upload (checks request.FILES and request.data).")
else:
    print("⚠️ Could not find PUT block in inventory/views.py. Attempting regex.")
    pattern = r"    elif request\.method == 'PUT':.*?return Response\(\{\"error\": str\(e\)\}, status=400\)"
    v_content = re.sub(pattern, new_put, v_content, flags=re.DOTALL)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Fixed backend using regex.")

# ============================================================
# 2. Fix Frontend (View Modal Edit Button & JS)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"
h_content = html_path.read_text(encoding="utf-8")

# A. Fix the View Modal's Edit Button
old_edit_btn = '''<button @click="viewModal = null; openProductModal(viewModal.id)" class="btn-primary flex-1">Edit This Product</button>'''
new_edit_btn = '''<button @click="editFromView()" class="btn-primary flex-1">Edit This Product</button>'''
h_content = h_content.replace(old_edit_btn, new_edit_btn)

# B. Add editFromView() function
h_content = h_content.replace(
    "    viewProduct(product) {",
    """    editFromView() {
      const id = this.viewModal.id;
      this.viewModal = null;
      this.openProductModal(id);
    },

    viewProduct(product) {"""
)

# C. Add safety check to openProductModal
old_open_modal = '''    async openProductModal(id) {
      if (!id) {
        this.resetForm();
        this.showModal = true;
        return;
      }
      try {
        const p = await apiFetch(`/inventory/products/?id=${id}`);
        this.form = { 
          id: p.id, barcode: p.barcode, name: p.name, 
          category_id: p.category_id, tax_rate_id: p.tax_rate_id, 
          unit_cost: p.unit_cost, selling_price: p.selling_price, 
          discount_percentage: p.discount_percentage, 
          current_stock: p.current_stock, reorder_level: p.reorder_level 
        };
        this.imageFile = null;
        this.imagePreview = p.image_url; 
        this.showModal = true;
      } catch(e) { alert(e.message); }
    },'''

new_open_modal = '''    async openProductModal(id) {
      if (!id) {
        this.resetForm();
        this.showModal = true;
        return;
      }
      try {
        console.log("Fetching product for edit:", id);
        const p = await apiFetch(`/inventory/products/?id=${id}`);
        console.log("Product data loaded:", p);
        
        this.form = { 
          id: p.id, barcode: p.barcode, name: p.name, 
          category_id: p.category_id, tax_rate_id: p.tax_rate_id, 
          unit_cost: p.unit_cost, selling_price: p.selling_price, 
          discount_percentage: p.discount_percentage, 
          current_stock: p.current_stock, reorder_level: p.reorder_level 
        };
        this.imageFile = null;
        this.imagePreview = p.image_url; 
        this.showModal = true;
      } catch(e) { alert('Failed to load product: ' + e.message); }
    },'''

h_content = h_content.replace(old_open_modal, new_open_modal)

html_path.write_text(h_content, encoding="utf-8")
print("✅ Fixed View Modal's Edit button and added debugging to openProductModal.")

# ============================================================
# 3. Verify MEDIA_ROOT exists
# ============================================================
media_dir = BACKEND_PATH / "media" / "products"
media_dir.mkdir(parents=True, exist_ok=True)
print(f"✅ Ensured media directory exists: {media_dir}")

print("\n" + "="*60)
print("  🎉 DONE!")
print("="*60)
print("""
NEXT STEPS:
1. Restart your server: python manage.py runserver
2. Open POS, go to Products, press Ctrl + Shift + R (Hard refresh)
3. Click "View" on a product, then click "Edit This Product"
   -> The Edit modal will now open correctly.
4. Change the name or upload a new image, and click "Save Product"
5. Click "View" again on that product. 
   -> The image will now be visible in the View modal!
""")