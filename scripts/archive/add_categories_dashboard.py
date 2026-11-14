import os
import re
import subprocess
import platform
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
# 1. Update Backend (Inventory Views - Category CRUD)
# ============================================================
views_path = BACKEND_PATH / "inventory" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

new_categories_view = '''
@api_view(["GET", "POST", "PUT"])
@permission_classes([IsAuthenticated])
def categories_list(request):
    if request.method == "GET":
        cats = Category.objects.filter(tenant=request.tenant)
        return Response([{
            "id": c.id, "name": c.name, "zra_item_code": c.zra_item_code, "is_active": c.is_active
        } for c in cats])
        
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    if request.method == "POST":
        c = Category.objects.create(
            tenant=request.tenant, name=data["name"], 
            zra_item_code=data.get("zra_item_code", "")
        )
        return Response({"success": True, "id": c.id}, status=201)
        
    elif request.method == "PUT":
        try:
            c = Category.objects.get(id=data["id"], tenant=request.tenant)
            c.name = data.get("name", c.name)
            c.zra_item_code = data.get("zra_item_code", c.zra_item_code)
            c.is_active = data.get("is_active", c.is_active)
            c.save()
            return Response({"success": True})
        except Category.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
'''
v_content = re.sub(r"@api_view\(\[\"GET\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef categories_list\(request\):.*?return Response\(\[.*?\]\)", new_categories_view.strip(), v_content, flags=re.DOTALL)
views_path.write_text(v_content, encoding="utf-8")
print("✅ Updated categories_list view")

# ============================================================
# 2. Update Backend (Reports Dashboard - Add Category Breakdown)
# ============================================================
reports_views = BACKEND_PATH / "reports" / "views.py"
r_content = reports_views.read_text(encoding="utf-8")

# Add category aggregation to the dashboard view
old_return = '''        "charts": {
            "trend": {"labels": trend_labels, "data": trend_data},
            "payments": {"labels": pm_labels, "data": pm_data},
            "top_products": {"labels": top_labels, "data": top_data}
        },'''

new_return = '''        "charts": {
            "trend": {"labels": trend_labels, "data": trend_data},
            "payments": {"labels": pm_labels, "data": pm_data},
            "top_products": {"labels": top_labels, "data": top_data},
            "category_breakdown": {"labels": cat_labels, "data": cat_data}
        },'''
patch_file(reports_views, old_return, new_return)

# Add the aggregation logic before the return statement
old_top_qs = '''    top_labels = [item['product__name'] for item in top_qs]
    top_data = [float(item['qty']) for item in top_qs]'''

new_top_qs = '''    top_labels = [item['product__name'] for item in top_qs]
    top_data = [float(item['qty']) for item in top_qs]

    # 5. Products by Category (Inventory Count)
    cat_qs = Product.objects.filter(tenant=request.tenant, company=request.branch, is_active=True) \\
        .values('category__name') \\
        .annotate(count=Count('id')) \\
        .order_by('-count')
        
    cat_labels = [item['category__name'] for item in cat_qs]
    cat_data = [item['count'] for item in cat_qs]'''
patch_file(reports_views, old_top_qs, new_top_qs)
print("✅ Updated reports/views.py with Category Breakdown")

# ============================================================
# 3. Add Route & Navigation
# ============================================================
views_web = BACKEND_PATH / "core" / "views_web.py"
web_content = views_web.read_text(encoding="utf-8")
if "def categories_page" not in web_content:
    web_content += "\n\ndef categories_page(request):\n    return render(request, 'pos/categories.html')\n"
    views_web.write_text(web_content, encoding="utf-8")

urls_web = BACKEND_PATH / "core" / "urls_web.py"
w_urls = urls_web.read_text(encoding="utf-8")
if "/categories" not in w_urls:
    w_urls = w_urls.replace(
        "urlpatterns = [",
        "urlpatterns = [\n    path('categories', views_web.categories_page, name='categories_page'),"
    )
    urls_web.write_text(w_urls, encoding="utf-8")

nav_path = BACKEND_PATH / "templates" / "pos" / "_nav.html"
nav_content = nav_path.read_text(encoding="utf-8")
if "href=\"/categories\"" not in nav_content:
    nav_content = nav_content.replace(
        '<a href="/tax-rates" class="nav-link"',
        '<a href="/categories" class="nav-link" x-show="[\'TENANT_OWNER\',\'MANAGER\'].includes(getUser()?.user_type)">Categories</a>\n    <a href="/tax-rates" class="nav-link"'
    )
    nav_path.write_text(nav_content, encoding="utf-8")
print("✅ Added Categories to Sidebar")

# ============================================================
# 4. Create Categories UI
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "categories.html"
new_html = '''
{% extends "pos/base.html" %}
{% block title %}Categories{% endblock %}
{% block body %}
<div class="h-screen flex">
  {% include "pos/_nav.html" %}
  <div class="flex-1 overflow-y-auto p-6" x-data="categoryApp()" x-init="load()">
    
    <div class="flex justify-between items-center mb-6">
      <h1 class="text-2xl font-bold">Product Categories</h1>
      <button @click="showModal = true; resetForm()" class="btn-primary">+ Add Category</button>
    </div>

    <div class="card overflow-hidden">
      <table class="w-full text-sm">
        <thead class="bg-gray-50 text-left text-xs uppercase text-gray-500">
          <tr>
            <th class="px-4 py-3">Category Name</th>
            <th class="px-4 py-3">ZRA Item Code</th>
            <th class="px-4 py-3">Status</th>
            <th class="px-4 py-3 text-right">Actions</th>
          </tr>
        </thead>
        <tbody>
          <template x-for="c in categories" :key="c.id">
            <tr class="border-t hover:bg-gray-50">
              <td class="px-4 py-3 font-medium" x-text="c.name"></td>
              <td class="px-4 py-3 font-mono text-xs" x-text="c.zra_item_code || '-'"></td>
              <td class="px-4 py-3">
                <span class="px-2 py-0.5 rounded text-xs" :class="c.is_active ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700'" x-text="c.is_active ? 'Active' : 'Inactive'"></span>
              </td>
              <td class="px-4 py-3 text-right">
                <button @click="editCategory(c)" class="text-brand-600 hover:underline text-xs">Edit</button>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>

    <!-- Add/Edit Modal -->
    <template x-if="showModal">
      <div class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
        <div class="bg-white rounded-xl max-w-sm w-full p-6">
          <h2 class="text-xl font-bold mb-4" x-text="form.id ? 'Edit Category' : 'New Category'"></h2>
          <form @submit.prevent="save()" class="space-y-4">
            
            <div>
              <label class="block text-sm mb-1">Category Name</label>
              <input type="text" x-model="form.name" placeholder="e.g. Soft Drinks" class="input-field" required>
            </div>
            
            <div>
              <label class="block text-sm mb-1">ZRA Item Code (UNSPSC)</label>
              <input type="text" x-model="form.zra_item_code" placeholder="e.g. 50202300" class="input-field">
            </div>

            <div x-show="form.id">
              <label class="flex items-center gap-2 text-sm">
                <input type="checkbox" x-model="form.is_active"> Active
              </label>
            </div>

            <div class="flex gap-2 mt-4">
              <button type="button" @click="showModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1">Save</button>
            </div>
          </form>
        </div>
      </div>
    </template>

  </div>
</div>
<script>
function categoryApp() {
  return {
    categories: [], showModal: false,
    form: { id: null, name: '', zra_item_code: '', is_active: true },

    async load() {
      if (!requireAuth()) return;
      try { this.categories = await apiFetch('/inventory/categories/'); } catch(e) { alert(e.message); }
    },

    resetForm() {
      this.form = { id: null, name: '', zra_item_code: '', is_active: true };
    },

    editCategory(c) {
      this.form = { ...c };
      this.showModal = true;
    },

    async save() {
      try {
        const method = this.form.id ? 'PUT' : 'POST';
        await apiFetch('/inventory/categories/', { method: method, body: JSON.stringify(this.form) });
        this.showModal = false;
        this.load();
      } catch(e) { alert(e.response?.data?.error || e.message); }
    }
  }
}
</script>
{% endblock %}
'''
html_path.write_text(new_html.strip(), encoding="utf-8")
print("✅ Created categories.html UI")

# ============================================================
# 5. Update Dashboard UI (Add Category Chart)
# ============================================================
dash_path = BACKEND_PATH / "templates" / "pos" / "dashboard.html"
d_content = dash_path.read_text(encoding="utf-8")

# Replace the Quick Tip card with a new Chart
old_tip = '''      <!-- Quick Info -->
      <div class="card p-6 bg-gradient-to-br from-brand-50 to-white border-brand-100">
        <h2 class="font-semibold mb-2 text-brand-700">Quick Tip</h2>
        <p class="text-sm text-gray-600">
          Use the <strong>Products</strong> tab to receive new stock when a delivery arrives. 
          Keeping inventory up to date ensures the POS never sells items you don't have.
        </p>
        <a href="/products" class="inline-block mt-4 btn-primary text-sm">Go to Inventory</a>
      </div>'''

new_tip = '''      <!-- Inventory by Category -->
      <div class="card p-6">
        <h2 class="font-semibold mb-4 text-gray-700">Inventory by Category</h2>
        <div class="relative h-64 w-full flex justify-center">
          <canvas id="categoryChart"></canvas>
        </div>
      </div>'''
patch_file(dash_path, old_tip, new_tip)

# Add JS to render the new chart
old_js = '''      // 3. Top Products (Bar)'''
new_js = '''      // 4. Products by Category (Doughnut)
      const catCtx = document.getElementById('categoryChart').getContext('2d');
      new Chart(catCtx, {
        type: 'polarArea',
        data: {
          labels: data.category_breakdown.labels.length ? data.category_breakdown.labels : ['No Data'],
          datasets: [{
            data: data.category_breakdown.data.length ? data.category_breakdown.data : [1],
            backgroundColor: data.category_breakdown.data.length ? palette : ['#e5e7eb'],
            borderWidth: 1
          }]
        },
        options: {
          responsive: true, maintainAspectRatio: false,
          plugins: { legend: { position: 'right', labels: { usePointStyle: true, boxWidth: 8 } } }
        }
      });

      // 3. Top Products (Bar)'''
patch_file(dash_path, old_js, new_js)

print("\n🎉 Done! Restart the server.")