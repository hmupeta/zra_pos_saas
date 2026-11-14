import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Backend: Reject Quotations without a Customer
# ============================================================
views_path = BACKEND_PATH / "sales" / "views.py"
v_content = views_path.read_text(encoding="utf-8")

# Add validation in quotations_list POST
old_post = '''    # POST: Create Quotation
    data = request.data
    items_data = data.get("items", [])
    if not items_data:
        return Response({"error": "Quotation must have items"}, status=400)

    import datetime
    q_num = f"QT-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
    
    quotation = Quotation.objects.create(
        tenant=request.tenant, company=request.branch,
        quotation_number=q_num, customer_id=data.get("customer_id"),
        customer_name=data.get("customer_name", "Walk-in Customer"),'''

new_post = '''    # POST: Create Quotation
    data = request.data
    items_data = data.get("items", [])
    
    if not items_data:
        return Response({"error": "Quotation must have at least one item"}, status=400)
        
    customer_id = data.get("customer_id")
    if not customer_id:
        return Response({"error": "Please select a registered customer. Quotations cannot be issued to unnamed customers."}, status=400)

    from customers.models import Customer
    try:
        customer = Customer.objects.get(id=customer_id, tenant=request.tenant)
        customer_name = customer.full_name
    except Customer.DoesNotExist:
        return Response({"error": "Customer not found."}, status=404)

    import datetime
    q_num = f"QT-{datetime.datetime.now().strftime('%y%m%d%H%M%S')}"
    
    quotation = Quotation.objects.create(
        tenant=request.tenant, company=request.branch,
        quotation_number=q_num, customer_id=customer.id,
        customer_name=customer_name,'''

if old_post in v_content:
    v_content = v_content.replace(old_post, new_post)
    views_path.write_text(v_content, encoding="utf-8")
    print("✅ Backend now rejects quotations without a customer.")

# ============================================================
# 2. Frontend: Remove "Walk-in" and force customer selection
# ============================================================
html_path = BACKEND_PATH / "templates" / "pos" / "quotations.html"
h_content = html_path.read_text(encoding="utf-8")

# Remove the "Walk-in Customer" option
old_select = '''                <select x-model="form.customer_id" @change="selectCustomer($event)" class="input-field flex-1">
                  <option value="">Walk-in Customer</option>
                  <template x-for="c in customers" :key="c.id">'''

new_select = '''                <select x-model="form.customer_id" @change="selectCustomer($event)" class="input-field flex-1" required>
                  <option value="" disabled selected>-- Select a Customer --</option>
                  <template x-for="c in customers" :key="c.id">'''

h_content = h_content.replace(old_select, new_select)

# Update selectCustomer JS function to not default to Walk-in
old_js = '''    selectCustomer(event) {
      const id = event.target.value;
      if (!id) {
        this.form.customer_name = 'Walk-in Customer';
        return;
      }
      const c = this.customers.find(x => x.id == id);
      if (c) this.form.customer_name = c.name;
    },'''

new_js = '''    selectCustomer(event) {
      const id = event.target.value;
      if (!id) {
        this.form.customer_name = '';
        return;
      }
      const c = this.customers.find(x => x.id == id);
      if (c) this.form.customer_name = c.name;
    },'''

h_content = h_content.replace(old_js, new_js)

# Update the Create Quote button to be disabled if no customer is selected
old_btn = '''            <button type="button" @click="saveQuotation()" class="btn-primary" :disabled="saving">
              <span x-text="saving ? 'Saving...' : (form.id ? 'Update Quote' : 'Create Quote')"></span>
            </button>'''

new_btn = '''            <button type="button" @click="saveQuotation()" class="btn-primary" :disabled="saving || !form.customer_id" :title="!form.customer_id ? 'Please select a customer first' : ''">
              <span x-text="saving ? 'Saving...' : (form.id ? 'Update Quote' : 'Create Quote')"></span>
            </button>'''

h_content = h_content.replace(old_btn, new_btn)

html_path.write_text(h_content, encoding="utf-8")
print("✅ Frontend updated. 'Walk-in Customer' removed, and button locked until a customer is chosen.")

print("\n🎉 Done! Restart the server and refresh the Quotations page.")