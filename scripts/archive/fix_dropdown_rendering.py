import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# 1. Fix the HTML structure of the dropdown
old_select = '''          <div x-show="availableMomoProviders.length > 0">
            <label class="block text-sm font-medium mb-1">Select Network</label>
            <select x-model="selectedProvider" class="input-field">
              <template x-for="p in availableMomoProviders" :key="p">
                <option :value="p" x-text="formatProviderName(p)"></option>
              </template>
            </select>
          </div>'''

new_select = '''          <div x-show="availableMomoProviders.length > 0">
            <label class="block text-sm font-medium mb-1">Select Network</label>
            <select x-model="selectedProvider" class="input-field">
              <template x-for="p in availableMomoProviders" :key="p">
                <option :value="p" x-text="formatProviderName(p)"></option>
              </template>
            </select>
            <!-- Debug info -->
            <p class="text-xs text-green-600 mt-1" x-show="availableMomoProviders.length > 0">
              Loaded: <span x-text="availableMomoProviders.join(', ')"></span>
            </p>
          </div>'''
content = content.replace(old_select, new_select)

# 2. Update the JS to ensure the array is populated properly
old_load = '''        // Load payment gateways for this branch
        try {
          this.paymentConfigs = await apiFetch('/payments/configs/');
          
          // Get unique providers that are Mobile Money
          const momoConfigs = this.paymentConfigs.filter(c => ['MTN_DIRECT', 'AIRTEL_DIRECT', 'ZAMTEL_DIRECT'].includes(c.provider));
          this.availableMomoProviders = [...new Set(momoConfigs.map(c => c.provider))];
          
          if (this.availableMomoProviders.length > 0) {
            this.selectedProvider = this.availableMomoProviders[0];
          }
        } catch(e) { console.error("Could not load gateways", e); }'''

new_load = '''        // Load payment gateways for this branch
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
content = content.replace(old_load, new_load)

# 3. Ensure formatProviderName is bulletproof
old_format = '''    formatProviderName(p) {
      const names = { 'MTN_DIRECT': 'MTN Mobile Money', 'AIRTEL_DIRECT': 'Airtel Money', 'ZAMTEL_DIRECT': 'Zamtel Kwacha' };
      return names[p] || p;
    },'''

new_format = '''    formatProviderName(p) {
      if (!p) return '';
      const names = { 
        'MTN_DIRECT': 'MTN Mobile Money', 
        'AIRTEL_DIRECT': 'Airtel Money', 
        'ZAMTEL_DIRECT': 'Zamtel Kwacha' 
      };
      return names[p] || p;
    },'''
content = content.replace(old_format, new_format)

pos_path.write_text(content, encoding="utf-8")
print("✅ Fixed POS Dropdown rendering and added debug logging")