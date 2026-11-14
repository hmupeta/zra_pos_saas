import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
file_path = BACKEND_PATH / "sales" / "receipt_service.py"

if not file_path.exists():
    print("❌ Could not find sales/receipt_service.py")
    exit(1)

content = file_path.read_text(encoding="utf-8")

# New method with VAT, Subtotal, and Clean Date
new_method = '''    def to_text(self):
        lines = [
            "=" * 42, self.invoice.company.name.center(42),
            f"TPIN: {self.invoice.company.tpin}".center(42), "=" * 42,
            f"Invoice: {self.invoice.invoice_number}",
            f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}",
            "-" * 42,
        ]
        for item in self.invoice.items.all():
            lines.append(f"{item.product.name[:25]:<28}{float(item.quantity):>4.0f} x {float(item.unit_price):>7.2f} = {float(item.total):>8.2f}")
        
        lines.extend([
            "", 
            "-" * 42, 
            f"{'Subtotal:':<28}K{float(self.invoice.subtotal):>10.2f}",
            f"{'VAT (16%):':<28}K{float(self.invoice.tax_total):>10.2f}",
            f"{'TOTAL:':<28}K{float(self.invoice.total):>10.2f}", 
            "=" * 42
        ])
        
        if self.invoice.zra_validation_code:
            lines.append(f"ZRA Code: {self.invoice.zra_validation_code}")
            
        return "\\n".join(lines)'''

# Regex to find the existing to_text method and replace it
pattern = r"    def to_text\(self\):.*?return \"\\n\"\.join\(lines\)"
if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_method, content, flags=re.DOTALL)
    file_path.write_text(content, encoding="utf-8")
    print("✅ Patched sales/receipt_service.py — Added Subtotal and VAT to receipt.")
else:
    print("❌ Could not find the to_text method to patch.")