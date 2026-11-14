import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Backend: Dynamic Currency in MoMo Service
# ============================================================
momo_path = BACKEND_PATH / "payments" / "momo_service.py"
m_content = momo_path.read_text(encoding="utf-8")

# Replace the hardcoded "ZMW" with dynamic logic
m_content = m_content.replace(
    '"currency": "ZMW",',
    '"currency": self.currency,'
)

# Add currency attribute to __init__
m_content = m_content.replace(
    'self.target_env = config.mtn_target_env',
    'self.target_env = config.mtn_target_env\n        self.currency = "EUR" if self.target_env == "sandbox" else "ZMW"'
)

momo_path.write_text(m_content, encoding="utf-8")
print("✅ Updated MTN MoMo service to use EUR for sandbox and ZMW for production")

# ============================================================
# 2. Frontend: Fix Dropdown & Payment Initiation
# ============================================================
pos_path = BACKEND_PATH / "templates" / "pos" / "pos.html"
p_content = pos_path.read_text(encoding="utf-8")

# Ensure the dropdown is populated and selectedProvider is set
old_load_logic = """        this.paymentConfigs = await apiFetch('/payments/configs/');
        this.availableMomoProviders = this.paymentConfigs.map(c => c.provider);
        if (this.availableMomoProviders.length > 0) { this.selectedProvider = this.availableMomoProviders[0]; }
        this.shift = await apiFetch('/sales/current-shift/');"""

new_load_logic = """        this.shift = await apiFetch('/sales/current-shift/');
        
        // Load payment gateways for this branch
        this.paymentConfigs = await apiFetch('/payments/configs/');
        // Filter only Mobile Money providers
        this.availableMomoProviders = this.paymentConfigs
          .filter(c => c.provider.includes('DIRECT'))
          .map(c => c.provider);
          
        if (this.availableMomoProviders.length > 0) {
          this.selectedProvider = this.availableMomoProviders[0];
        }"""

p_content = p_content.replace(old_load_logic, new_load_logic)

# Add a fallback in doCheckout to ensure a provider is selected
p_content = p_content.replace(
    "if (this.paymentMethod === 'MOMO') {",
    "if (this.paymentMethod === 'MOMO') {\n          if (!this.selectedProvider) {\n            alert('Please select a network first. If none appear, configure a gateway in Settings.');\n            this.busy = false; return;\n          }"
)

pos_path.write_text(p_content, encoding="utf-8")
print("✅ Fixed POS frontend to correctly populate the Network dropdown")

print("\n🎉 Done! Restart the server.")