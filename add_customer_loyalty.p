import os
from pathlib import Path
import re

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
# 1. Update Models: Link Invoice to Customer
# ============================================================
# Check if Customer model has total_spent
cust_model = BACKEND_PATH / "customers" / "models.py"
c_content = cust_model.read_text(encoding="utf-8")
if "total_spent" not in c_content:
    c_content = c_content.replace(
        "loyalty_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)",
        "loyalty_points = models.DecimalField(max_digits=10, decimal_places=2, default=0)\n    total_spent = models.DecimalField(max_digits=12, decimal_places=2, default=0)"
    )
    cust_model.write_text(c_content, encoding="utf-8")

# Add customer ForeignKey to Invoice
sales_model = BACKEND_PATH / "sales" / "models.py"
s_content = sales_model.read_text(encoding="utf-8")
if "customer = models.ForeignKey" not in s_content:
    s_content = s_content.replace(
        "customer_name = models.CharField(max_length=200, default='Cash Customer')",
        "customer = models.ForeignKey('customers.Customer', on_delete=models.SET_NULL, null=True, blank=True)\n    customer_name = models.CharField(max_length=200, default='Cash Customer')"
    )
    sales_model.write_text(s_content, encoding="utf-8")
print("✅ Updated Customer and Invoice models")

# ============================================================
# 2. Update Cart & Checkout Logic
# ============================================================
cart_service = BACKEND_PATH / "sales" / "cart_service.py"
c_service_content = cart_service.read_text(encoding="utf-8")

# Add customer_id to cart init
c_service_content = c_service_content.replace(
    '"customer_name": cart.get("customer_name", "Cash Customer"),',
    '"customer_name": cart.get("customer_name", "Cash Customer"),\n            customer_id=cart.get("customer_id"),'
)

# Update checkout to award loyalty points
new_checkout_logic = '''
        # Award Loyalty Points
        if invoice.customer:
            points_earned = int(invoice.total / 10) # 1 point per K10
            invoice.customer.loyalty_points += points_earned
            invoice.customer.total_spent += invoice.total
            invoice.customer.save()
            
        CartService.clear(tenant_id, branch_id, shift.id)
        return invoice
'''
c_service_content = re.sub(r"CartService\.clear\(tenant_id, branch_id, shift\.id\)\s*return invoice", new_checkout_logic.strip(), c_service_content)
cart_service.write_text(c_service_content, encoding="utf-8")
print("✅ Updated CartService for loyalty points")

# Update Cart Customer Endpoint to accept ID
sales_views = BACKEND_PATH / "sales" / "views.py"
sv_content = sales_views.read_text(encoding="utf-8")
new_update_cart = '''
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def update_cart_customer(request):
    shift = Shift.objects.filter(cashier=request.user, is_closed=False).first()
    if not shift:
        return Response({"error": "No open shift"}, status=400)
    
    customer_id = request.data.get("customer_id")
    customer_name = request.data.get("customer_name", "Cash Customer").strip()
        
    cart = CartService.get(request.tenant.id, request.branch.id, shift.id)
    
    if customer_id:
        from customers.models import Customer
        try:
            cust = Customer.objects.get(pk=customer_id, tenant=request.tenant)
            cart["customer_id"] = cust.id
            cart["customer_name"] = cust.full_name
        except Customer.DoesNotExist:
            pass
    else:
        cart["customer_id"] = None
        cart["customer_name"] = customer_name if customer_name else "Cash Customer"
        
    CartService.save(request.tenant.id, request.branch.id, shift.id, cart)
    
    return Response({"success": True, "customer_name": cart["customer_name"]})
'''
sv_content = re.sub(r"@api_view\(\[\"POST\"\]\)\ndef update_cart_customer\(request\):.*?return Response\(\{\"success\": True, \"customer_name\": customer_name\}\)", new_update_cart.strip(), sv_content, flags=re.DOTALL)
sales_views.write_text(sv_content, encoding="utf-8")
print("✅ Updated update_cart_customer view")

# ============================================================
# 3. Customer API Endpoints
# ============================================================
cust_views = BACKEND_PATH / "customers" / "views.py"
new_cust_views = '''
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.db.models import Q
from .models import Customer
import uuid

@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def customers_list(request):
    if request.method == "GET":
        q = request.query_params.get("search", "")
        qs = Customer.objects.filter(tenant=request.tenant).order_by("-total_spent")
        if q:
            qs = qs.filter(Q(first_name__icontains=q) | Q(last_name__icontains=q) | Q(phone_number__icontains=q))
            
        return Response([{
            "id": c.id, "name": c.full_name, "phone": c.phone_number,
            "loyalty_points": float(c.loyalty_points), "total_spent": float(c.total_spent)
        } for c in qs[:50]])
        
    # POST: Quick Create from POS
    data = request.data
    phone = data.get("phone_number")
    if Customer.objects.filter(tenant=request.tenant, phone_number=phone).exists():
        return Response({"error": "Phone number already registered"}, status=400)
        
    c = Customer.objects.create(
        tenant=request.tenant, company=request.branch,
        customer_id=f"CUST{uuid.uuid4().hex[:6].upper()}",
        first_name=data.get("first_name", "Walk-in"),
        last_name=data.get("last_name", ""),
        phone_number=phone
    )
    return Response({"success": True, "id": c.id, "name": c.full_name})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def customer_search_pos(request):
    """Lightweight search for the POS dropdown"""
    q = request.query_params.get("q", "")
    if not q or len(q) < 3:
        return Response([])
    qs = Customer.objects.filter(tenant=request.tenant).filter(
        Q(phone_number__icontains=q) | Q(first_name__icontains=q)
    )[:5]
    return Response([{"id": c.id, "name": c.full_name, "phone": c.phone_number, "points": float(c.loyalty_points)} for c in qs])
'''
cust_views.write_text(new_cust_views.strip(), encoding="utf-8")

cust_urls = BACKEND_PATH / "customers" / "urls.py"
new_cust_urls = '''
from django.urls import path
from . import views

urlpatterns = [
    path('', views.customers_list, name='customers_list'),
    path('pos-search/', views.customer_search_pos, name='customer_search_pos'),
]
'''
cust_urls.write_text(new_cust_urls.strip(), encoding="utf-8")
print("✅ Created Customer API endpoints")

# ============================================================
# 4. Update POS UI (HTML & JS)
# ============================================================
pos_html = BACKEND_PATH / "templates" / "pos" / "pos.html"
html_content = pos_html.read_text(encoding="utf-8")

# Replace the old simple text input with a search dropdown
old_input = '''        <!-- Customer Name Input (ONLY ONE) -->
        <div class="px-4 py-2 border-b bg-gray-50">
          <input type="text" x-model="customerName" @change="updateCustomer()" placeholder="Customer Name (Optional)" class="w-full px-2 py-1 text-sm border rounded">
        </div>'''

new_input = '''        <!-- Customer Search & Selection -->
        <div class="px-4 py-2 border-b bg-gray-50 relative">
          <div class="flex gap-2">
            <input type="text" x-model="customerSearch" @input.debounce.300ms="searchCustomers()" @focus="showCustDropdown = true" placeholder="Search Phone or Name..." class="w-full px-2 py-1 text-sm border rounded">
            <button @click="showNewCustModal = true" class="bg-brand-100 text-brand-700 px-2 rounded text-sm font-bold hover:bg-brand-200" title="Add New Customer">+</button>
          </div>
          
          <!-- Selected Customer Badge -->
          <template x-if="customerName">
            <div class="mt-2 flex justify-between items-center bg-green-50 px-2 py-1 rounded border border-green-200">
              <span class="text-xs font-medium text-green-800" x-text="customerName"></span>
              <button @click="clearCustomer()" class="text-green-600 hover:text-green-900 text-xs font-bold">✕</button>
            </div>
          </template>

          <!-- Dropdown Results -->
          <div x-show="showCustDropdown && customerResults.length > 0" @click.away="showCustDropdown = false" class="absolute left-0 right-0 mt-1 bg-white border shadow-lg rounded z-20 mx-4 max-h-48 overflow-y-auto">
            <template x-for="c in customerResults" :key="c.id">
              <div @click="selectCustomer(c)" class="p-2 border-b hover:bg-gray-50 cursor-pointer">
                <div class="text-sm font-medium" x-text="c.name"></div>
                <div class="text-xs text-gray-500"><span x-text="c.phone"></span> · Points: <span x-text="c.points"></span></div>
              </div>
            </template>
          </div>
        </div>'''

html_content = html_content.replace(old_input, new_input)

# Update JS variables
html_content = html_content.replace(
    "search: '', busy: false, lastScan: null, customerName: '',",
    "search: '', busy: false, lastScan: null, customerName: '', customerId: null,\n    customerSearch: '', customerResults: [], showCustDropdown: false, showNewCustModal: false,\n    newCust: { first_name: '', last_name: '', phone_number: '' },"
)

# Add methods
new_js_methods = '''
    async searchCustomers() {
      if (this.customerSearch.length < 3) { this.customerResults = []; return; }
      try {
        this.customerResults = await apiFetch(`/customers/pos-search/?q=${this.customerSearch}`);
        this.showCustDropdown = true;
      } catch(e) { console.error(e); }
    },

    selectCustomer(c) {
      this.customerId = c.id;
      this.customerName = c.name;
      this.customerSearch = '';
      this.customerResults = [];
      this.showCustDropdown = false;
      this.updateCustomer();
    },

    clearCustomer() {
      this.customerId = null;
      this.customerName = '';
      this.updateCustomer();
    },

    async createNewCustomer() {
      try {
        const res = await apiFetch('/customers/', { method: 'POST', body: JSON.stringify(this.newCust) });
        this.selectCustomer({ id: res.id, name: res.name });
        this.showNewCustModal = false;
        this.newCust = { first_name: '', last_name: '', phone_number: '' };
      } catch(e) { alert(e.response?.data?.error || e.message); }
    },

    async updateCustomer() {
      if (!this.shift) return;
      try {
        await apiFetch('/sales/cart/customer/', {
          method: 'POST',
          body: JSON.stringify({ customer_id: this.customerId, customer_name: this.customerName })
        });
      } catch (e) { console.error('Failed to update customer', e); }
    },
'''
html_content = html_content.replace("    async updateCustomer() {", new_js_methods.strip() + "\n\n    /* old updateCustomer removed */ async updateCustomerOld() {")

# Clear customer on checkout
html_content = html_content.replace("this.customerName = '';", "this.customerName = ''; this.customerId = null;")

# Add New Customer Modal at the end of the body
modal_html = '''
    <!-- Add Customer Modal -->
    <div x-show="showNewCustModal" x-cloak class="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
      <div class="bg-white rounded-xl max-w-sm w-full p-6">
        <h2 class="text-xl font-bold mb-4">New Customer</h2>
        <form @submit.prevent="createNewCustomer()" class="space-y-3">
          <input type="text" x-model="newCust.phone_number" placeholder="Phone Number" class="input-field" required>
          <input type="text" x-model="newCust.first_name" placeholder="First Name" class="input-field" required>
          <input type="text" x-model="newCust.last_name" placeholder="Last Name" class="input-field">
          <div class="flex gap-2 mt-4">
            <button type="button" @click="showNewCustModal = false" class="btn-secondary flex-1">Cancel</button>
            <button type="submit" class="btn-primary flex-1">Save</button>
          </div>
        </form>
      </div>
    </div>
'''
html_content = html_content.replace("  </div>\n</div>\n\n<script>", "  </div>\n" + modal_html + "\n</div>\n\n<script>")
pos_html.write_text(html_content, encoding="utf-8")
print("✅ Updated POS UI with Customer Search and Quick Add")

# ============================================================
# 5. Run Migrations
# ============================================================
print("Running migrations...")
import subprocess
import platform
venv = BACKEND_PATH / "venv"
python = venv / ("Scripts/python.exe" if platform.system() == "Windows" else "bin/python")

subprocess.run([str(python), "manage.py", "makemigrations", "customers"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "makemigrations", "sales"], cwd=BACKEND_PATH)
subprocess.run([str(python), "manage.py", "migrate"], cwd=BACKEND_PATH)
print("\n🎉 Done! Restart the server.")