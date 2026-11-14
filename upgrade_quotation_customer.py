import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "quotations.html"

content = html_path.read_text(encoding="utf-8")

# ============================================================
# 1. Replace the Customer Name input with a dropdown + New button
# ============================================================
old_input = '''            <input placeholder="Customer Name (Optional)" x-model="form.customer_name" class="input-field">'''

new_input = '''            <div class="flex gap-2">
              <select x-model="form.customer_id" @change="selectCustomer($event)" class="input-field flex-1">
                <option value="">Walk-in Customer</option>
                <template x-for="c in customers" :key="c.id">
                  <option :value="c.id" x-text="c.name + ' (' + c.phone + ')'"></option>
                </template>
              </select>
              <button type="button" @click.prevent="showCustomerModal = true" class="btn-secondary px-3" title="Add New Customer">
                <i data-lucide="plus" class="w-4 h-4"></i>
              </button>
            </div>'''

if old_input in content:
    content = content.replace(old_input, new_input)
    print("✅ Replaced Customer Name input with Dropdown.")
else:
    print("⚠️ Could not find exact input. Checking for variations.")
    # Fallback regex if the exact string doesn't match
    pattern = r'<input placeholder="Customer Name \(Optional\)".*?>'
    if re.search(pattern, content):
        content = re.sub(pattern, new_input, content)
        print("✅ Replaced input using regex fallback.")

# ============================================================
# 2. Add the New Customer Modal HTML
# ============================================================
customer_modal = '''
    <!-- Quick Add Customer Modal -->
    <template x-if="showCustomerModal">
      <div class="fixed inset-0 bg-black/60 flex items-center justify-center z-[9999] p-4 backdrop-blur-sm">
        <div class="bg-white rounded-xl max-w-sm w-full p-6 shadow-2xl">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold">New Customer</h2>
            <button @click="showCustomerModal = false" class="text-gray-400 hover:text-red-500 font-bold text-xl">&times;</button>
          </div>
          <form @submit.prevent="createNewCustomer()" class="space-y-3">
            <input type="text" x-model="newCust.phone_number" placeholder="Phone Number" class="input-field" required>
            <input type="text" x-model="newCust.first_name" placeholder="First Name" class="input-field" required>
            <input type="text" x-model="newCust.last_name" placeholder="Last Name (Optional)" class="input-field">
            <div class="flex gap-2 mt-4">
              <button type="button" @click="showCustomerModal = false" class="btn-secondary flex-1">Cancel</button>
              <button type="submit" class="btn-primary flex-1" :disabled="savingCustomer">
                <span x-show="!savingCustomer">Save Customer</span>
                <span x-show="savingCustomer">Saving...</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </template>
'''

if "<!-- Quick Add Customer Modal -->" not in content:
    # Insert before the closing div of the main x-data container
    content = content.replace("  </div>\n</div>\n<script>", customer_modal + "\n  </div>\n</div>\n<script>")
    print("✅ Added Quick Add Customer Modal.")

# ============================================================
# 3. Update JavaScript State and Functions
# ============================================================
# Add new state variables
old_state = "quotations: [], products: [], showModal: false, saving: false,"
new_state = "quotations: [], products: [], customers: [], showModal: false, showCustomerModal: false, saving: false, savingCustomer: false,\n    newCust: { first_name: '', last_name: '', phone_number: '' },"
content = content.replace(old_state, new_state)

# Update form state to include customer_id
old_form = "form: { customer_name: '', valid_until: '', items: [{product_id:'', quantity:1}] },"
new_form = "form: { customer_id: '', customer_name: '', valid_until: '', items: [{product_id:'', quantity:1}] },"
content = content.replace(old_form, new_form)

# Update load() to fetch customers
old_load = "this.quotations = await apiFetch('/sales/quotations/');\n        this.products = await apiFetch('/inventory/products/');"
new_load = "this.quotations = await apiFetch('/sales/quotations/');\n        this.products = await apiFetch('/inventory/products/');\n        this.customers = await apiFetch('/customers/');"
content = content.replace(old_load, new_load)

# Update openModal/create reset logic to include customer_id
old_reset = "this.form = { customer_name: '', valid_until: '', items: [{product_id:'', quantity:1}] };"
new_reset = "this.form = { customer_id: '', customer_name: '', valid_until: '', items: [{product_id:'', quantity:1}] };"
content = content.replace(old_reset, new_reset)

# Add selectCustomer and createNewCustomer functions
new_functions = '''
    selectCustomer(event) {
      const id = event.target.value;
      if (!id) {
        this.form.customer_name = 'Walk-in Customer';
        return;
      }
      const c = this.customers.find(x => x.id == id);
      if (c) {
        this.form.customer_name = c.name;
      }
    },

    async createNewCustomer() {
      this.savingCustomer = true;
      try {
        const res = await apiFetch('/customers/', { method: 'POST', body: JSON.stringify(this.newCust) });
        this.customers = await apiFetch('/customers/');
        this.form.customer_id = res.id;
        this.form.customer_name = res.name;
        
        this.showCustomerModal = false;
        this.newCust = { first_name: '', last_name: '', phone_number: '' };
      } catch (e) {
        alert(e.response?.data?.error || e.message);
      } finally {
        this.savingCustomer = false;
      }
    },
'''

if "selectCustomer(event)" not in content:
    content = content.replace("    getPrice(id) {", new_functions + "\n    getPrice(id) {")
    print("✅ Added selectCustomer and createNewCustomer JS functions.")

html_path.write_text(content, encoding="utf-8")

print("\n🎉 Done! Restart the server and refresh the Quotations page.")