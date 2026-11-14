import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

def patch_file(path, old, new, is_regex=False):
    if not path.exists(): return
    content = path.read_text(encoding="utf-8")
    if is_regex:
        content = re.sub(old, new, content, flags=re.DOTALL)
    else:
        content = content.replace(old, new)
    path.write_text(content, encoding="utf-8")

# ============================================================
# 1. Update Backend (inventory/views.py) to handle PUT (Edit)
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Add logic to products_list to handle GET(id), PUT, DELETE
new_products_list = '''
@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def products_list(request):
    if request.method == 'GET':
        # Check if a specific ID is requested
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
                    "image_url": p.image.url if getattr(p, "image", None) else None,
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
                "image_url": p.image.url if getattr(p, "image", None) else None,
            })
        return Response(data)
        
    elif request.method == 'PUT':
        # Edit existing product
        data = request.data
        product_id = request.data.get("id")
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
            
            if request.FILES.get("image"):
                p.image = request.FILES.get("image")
                
            p.save()
            return Response({"success": True, "id": p.id})
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

# Replace the whole products_list view
v_content = re.sub(r"@api_view\(\['GET', 'POST'\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef products_list\(request\):.*?return Response\(\{\"error\": str\(e\)\}, status=400\)", new_products_list.strip(), v_content, flags=re.DOTALL)
views_path.write_text(v_content, encoding="utf-8")
print("✅ Updated inventory/views.py to support Editing")

# ============================================================
# 2. Update Frontend (products.html)
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "products.html"
html_content = html_path.read_text(encoding="utf-8")

# Add Edit button to the Actions column
old_actions = '''<td class="px-4 py-3 text-right">
                <button @click="openReceiveModal(p)" class="text-xs text-brand-600 hover:underline">Add Stock</button>
              </td>'''
new_actions = '''<td class="px-4 py-3 text-right space-x-3">
                <button @click="editProduct(p.id)" class="text-xs text-gray-500 hover:text-brand-600 hover:underline">Edit</button>
                <button @click="openReceiveModal(p)" class="text-xs text-brand-600 hover:underline">Add Stock</button>
              </td>'''
html_content = html_content.replace(old_actions, new_actions)

# Update the Modal title to be dynamic
html_content = html_content.replace('<h2 class="text-xl font-bold mb-4">New Product</h2>', '<h2 class="text-xl font-bold mb-4" x-text="form.id ? \'Edit Product\' : \'New Product\'"></h2>')

# Update the form submission to handle both POST and PUT, and show loading state
old_submit = '''    async create() {
      this.saving = true;
      try {
        const fd = new FormData();
        Object.keys(this.form).forEach(k => fd.append(k, this.form[k]));
        if (this.imageFile) fd.append('image', this.imageFile);

        await apiFetch('/inventory/products/', { method: 'POST', body: fd });
        
        this.showModal = false;
        this.form = { barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', discount_percentage: 0, current_stock: 0, reorder_level: 10 };
        this.imageFile = null;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    },'''

new_submit = '''    async create() {
      this.saving = true;
      try {
        const fd = new FormData();
        Object.keys(this.form).forEach(k => fd.append(k, this.form[k]));
        if (this.imageFile) fd.append('image', this.imageFile);

        const method = this.form.id ? 'PUT' : 'POST';
        await apiFetch('/inventory/products/', { method: method, body: fd });
        
        this.showModal = false;
        this.resetForm();
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
      finally { this.saving = false; }
    },

    async editProduct(id) {
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
        this.showModal = true;
      } catch(e) { alert(e.message); }
    },

    resetForm() {
      this.form = { barcode: '', name: '', category_id: '', tax_rate_id: '', unit_cost: '', selling_price: '', discount_percentage: 0, current_stock: 0, reorder_level: 10 };
      this.imageFile = null;
    },'''

html_content = html_content.replace(old_submit, new_submit)

# Update the Cancel/Close button to reset the form so it doesn't stay in "Edit" mode
html_content = html_content.replace('<button type="button" @click="showModal = false" class="btn-secondary flex-1">Cancel</button>', '<button type="button" @click="showModal = false; resetForm()" class="btn-secondary flex-1">Cancel</button>')

html_path.write_text(html_content, encoding="utf-8")
print("✅ Updated Products UI with Edit functionality")
print("🎉 Done! Restart the server.")