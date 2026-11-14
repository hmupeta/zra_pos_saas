import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# 1. Replace the custom div dropdown with a native <select>
pattern = r'<div x-show="availableMomoProviders\.length > 0" class="relative" x-data="\{ open: false \}">.*?</div>\s*</div>'
new_select = '''          <div x-show="availableMomoProviders.length > 0">
            <label class="block text-sm font-medium mb-1">Select Network</label>
            <select x-model="selectedProvider" class="input-field bg-white">
              <template x-for="p in availableMomoProviders" :key="p">
                <option :value="p" x-text="formatProviderName(p)"></option>
              </template>
            </select>
          </div>'''

if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_select, content, flags=re.DOTALL)
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Replaced custom dropdown with native select.")
else:
    # If regex fails, fallback to simple string replacement
    old_block = '''          <div x-show="availableMomoProviders.length > 0" class="relative" x-data="{ open: false }">
            <label class="block text-sm font-medium mb-1">Select Network</label>
            
            <!-- Dropdown Button -->
            <button type="button" @click="open = !open" @click.away="open = false" class="input-field bg-white flex justify-between items-center w-full text-left">
              <span x-text="selectedProvider ? formatProviderName(selectedProvider) : 'Select a network...'"></span>
              <i data-lucide="chevron-down" class="w-4 h-4 text-gray-400"></i>
            </button>
            
            <!-- Dropdown Menu -->
            <div x-show="open" x-cloak class="absolute z-50 mt-1 w-full bg-white shadow-lg max-h-60 rounded-md py-1 text-base ring-1 ring-black ring-opacity-5 overflow-auto focus:outline-none sm:text-sm">
              <template x-for="p in availableMomoProviders" :key="p">
                <div @click="selectedProvider = p; open = false" class="cursor-pointer select-none relative py-2 pl-3 pr-9 hover:bg-indigo-50 text-slate-900">
                  <span x-text="formatProviderName(p)" class="font-normal block truncate"></span>
                  <span x-show="selectedProvider === p" class="text-indigo-600 absolute inset-y-0 right-0 flex items-center pr-4">
                    <i data-lucide="check" class="w-4 h-4"></i>
                  </span>
                </div>
              </template>
            </div>
          </div>'''
          
    if old_block in content:
        content = content.replace(old_block, new_select)
        pos_path.write_text(content, encoding="utf-8")
        print("✅ Replaced custom dropdown with native select (exact match).")
    else:
        print("⚠️ Could not find the dropdown block to replace. Please check the file manually.")

# 2. Ensure the JS correctly populates the array
old_js = '''        // Load payment gateways for this branch
        try {
          this.paymentConfigs = await apiFetch('/payments/configs/');
          console.log("Loaded Payment Configs:", this.paymentConfigs);
          
          if (this.paymentConfigs && this.paymentConfigs.length > 0) {
            // Get all mobile money providers
            const momoConfigs = this.paymentConfigs.filter(c => c.provider.includes('DIRECT'));
            this.availableMomoProviders = momoConfigs.map(c => c.provider);
            
            // Remove duplicates just in case
            this.availableMomoProviders = [...new Set(this.availableMomoProviders)];
            
            console.log("Available MoMo Providers:", this.availableMomoProviders);
            
            if (this.availableMomoProviders.length > 0) {
              this.selectedProvider = this.availableMomoProviders[0];
            }
          }
        } catch(e) { 
          console.error("Could not load gateways", e); 
        }'''

new_js = '''        // Load payment gateways for this branch
        try {
          this.paymentConfigs = await apiFetch('/payments/configs/');
          
          if (this.paymentConfigs && Array.isArray(this.paymentConfigs)) {
            // Get all mobile money providers
            const momoConfigs = this.paymentConfigs.filter(c => c.provider.includes('DIRECT'));
            this.availableMomoProviders = momoConfigs.map(c => c.provider);
            
            // Remove duplicates
            this.availableMomoProviders = [...new Set(this.availableMomoProviders)];
            
            if (this.availableMomoProviders.length > 0) {
              this.selectedProvider = this.availableMomoProviders[0];
            }
          }
        } catch(e) { 
          console.error("Could not load gateways", e); 
        }'''

if old_js in content:
    content = content.replace(old_js, new_js)
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Fixed POS JavaScript to safely populate the dropdown.")
else:
    print("⚠️ Could not find the JS block to replace.")