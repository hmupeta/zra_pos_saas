import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"

content = pos_path.read_text(encoding="utf-8")

# 1. Find the native <select> block and replace it with a custom styled div
old_select = '''          <div x-show="availableMomoProviders.length > 0">
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

new_select = '''          <div x-show="availableMomoProviders.length > 0" class="relative" x-data="{ open: false }">
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

if old_select in content:
    content = content.replace(old_select, new_select)
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Replaced native select with custom Alpine.js dropdown.")
else:
    # Fallback in case of whitespace mismatch
    pattern = r'<div x-show="availableMomoProviders\.length > 0">.*?Loaded: <span x-text="availableMomoProviders\.join\(\', \'\)"></span>.*?</div>'
    content = re.sub(pattern, new_select, content, flags=re.DOTALL)
    pos_path.write_text(content, encoding="utf-8")
    print("✅ Replaced native select with custom Alpine.js dropdown using regex.")

print("\n🎉 Done! Restart the server and refresh the POS.")