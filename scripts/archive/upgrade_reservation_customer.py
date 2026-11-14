import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
html_path = BACKEND_PATH / "templates" / "pos" / "reservations.html"

content = html_path.read_text(encoding="utf-8")

# ============================================================
# 1. Replace the Customer Name input with a dropdown + New button
# ============================================================
old_input = '''            <div>
              <label class="block text-sm mb-1">Customer Name</label>
              <input type="text" x-model="form.customer_name" placeholder="e.g. John Banda" class="input-field" required>
            </div>'''

new_input = '''            <div>
              <label class="block text-sm mb-1">Customer</label>
              <div class="flex gap-2">
                <select x-model="form.customer_id" @change="selectCustomer($event)" class="input-field flex-1">
                  <option value="">Walk-in Customer</option>
                  <template x-for="c in customers" :key="c.id">
                    <option :value="c.id" x-text="c.name + ' (' + c.phone + ')'"></option>
                  </template>
                </select>
                <button @click.prevent="showCustomerModal = true" class="btn-secondary px-3" title="Add New Customer">
                  <i data-lucide="plus" class="w-4 h-4"></i>
                </button>
              </div>
            </div>'''

if old_input in content:
    content = content.replace(old_input, new_input)
    print("✅ Replaced Customer Name input with Dropdown.")
else:
    print("⚠️ Could not find Customer Name input. Checking for variations.")
    # Fallback if the exact string doesn't match
    pattern = r'<label class="block text-sm mb-1">Customer Name</label>.*?<input type="text".*?>'
    if re.search(pattern, content, flags=re.DOTALL):
        content = re.sub(pattern, new_input, content, flags=re.DOTALL)
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
    content = content.replace("  </div>\n</div>\n<script>", customer_modal + "\n  </div>\n</div>\n<script>")
    print("✅ Added Quick Add Customer Modal.")

# ============================================================
# 3. Update JavaScript State and Functions
# ============================================================
# Add new state variables
old_state = "reservations: [], products: [], showModal: false, saving: false,"
new_state = "reservations: [], products: [], customers: [], showModal: false, showCustomerModal: false, saving: false, savingCustomer: false,\n    newCust: { first_name: '', last_name: '', phone_number: '' },"
content = content.replace(old_state, new_state)

# Update load() to fetch customers
old_load = "this.reservations = await apiFetch('/sales/reservations/');\n        this.products = await apiFetch('/inventory/products/');"
new_load = "this.reservations = await apiFetch('/sales/reservations/');\n        this.products = await apiFetch('/inventory/products/');\n        this.customers = await apiFetch('/customers/');"
content = content.replace(old_load, new_load)

# Update openModal() to reset customer_id
old_open = "this.form = { customer_name: '', customer_phone: '', valid_until: '', deposit_paid: 0, items: [{product_id:'', quantity:1, stock_ok:true, stock_text:'-'}] };"
new_open = "this.form = { customer_id: '', customer_name: '', customer_phone: '', valid_until: '', deposit_paid: 0, items: [{product_id:'', quantity:1, stock_ok:true, stock_text:'-'}] };"
content = content.replace(old_open, new_open)

# Add selectCustomer and createNewCustomer functions
new_functions = '''
    selectCustomer(event) {
      const id = event.target.value;
      if (!id) {
        this.form.customer_name = 'Walk-in Customer';
        this.form.customer_phone = '';
        return;
      }
      const c = this.customers.find(x => x.id == id);
      if (c) {
        this.form.customer_name = c.name;
        this.form.customer_phone = c.phone;
      }
    },

    async createNewCustomer() {
      this.savingCustomer = true;
      try {
        const res = await apiFetch('/customers/', { method: 'POST', body: JSON.stringify(this.newCust) });
        // Refresh customer list
        this.customers = await apiFetch('/customers/');
        // Auto-select the new customer
        this.form.customer_id = res.id;
        this.form.customer_name = res.name;
        this.form.customer_phone = this.newCust.phone_number;
        
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
    content = content.replace("    checkStock(line) {", new_functions + "\n    checkStock(line) {")
    print("✅ Added selectCustomer and createNewCustomer JS functions.")

html_path.write_text(content, encoding="utf-8")

print("\n🎉 Done! Restart the server and refresh the Reservations page.")