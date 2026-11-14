from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
file_path = BACKEND_PATH / "sales" / "receipt_service.py"

correct_code = '''
class ReceiptService:
    ESC, GS = "\\x1b", "\\x1d"

    def __init__(self, invoice):
        self.invoice = invoice

    def to_escpos(self, width=80):
        cpl = 32 if width == 58 else 42
        lines = [
            self.ESC + "@",
            self.ESC + "a\\x01",
            self.invoice.company.name + "\\n",
            self.ESC + "a\\x00",
            self.invoice.company.address[:cpl] + "\\n",
            f"TPIN: {self.invoice.company.tpin}\\n",
            "-" * cpl + "\\n",
            f"Invoice: {self.invoice.invoice_number}\\n",
            f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}\\n",
        ]
        
        # Add Customer Name if it exists
        if self.invoice.customer_name and self.invoice.customer_name != "Cash Customer":
            lines.append(f"Customer: {self.invoice.customer_name}\\n")
            
        lines.append("-" * cpl + "\\n")
        
        for item in self.invoice.items.all():
            lines.append(f"{item.product.name[:18]:<20}{int(item.quantity):>3}{float(item.unit_price):>6.2f}{float(item.total):>8.2f}\\n")
            
        lines.extend([
            "-" * cpl + "\\n",
            f"{'Subtotal:':<25}K{float(self.invoice.subtotal):>10.2f}\\n",
            f"{'VAT (16%):':<25}K{float(self.invoice.tax_total):>10.2f}\\n",
            "-" * cpl + "\\n",
            self.ESC + "!\\x10", # Double height for total
            f"{'TOTAL:':<25}K{float(self.invoice.total):>10.2f}\\n",
            self.ESC + "!\\x00",
            "-" * cpl + "\\n",
        ])
        
        if self.invoice.zra_validation_code:
            lines.append(self.ESC + "a\\x01")
            lines.append("ZRA SMART INVOICE\\n")
            lines.append(f"Code: {self.invoice.zra_validation_code}\\n")
            lines.append(self.ESC + "a\\x00")
            
        lines.append("\\n")
        lines.append(self.ESC + "a\\x01")
        lines.append("Thank you for your business!\\n")
        lines.append("\\n\\n\\n")
        lines.append(self.GS + "V\\x42\\x00")
        
        return "".join(lines).encode("latin-1", errors="replace")

    def to_text(self):
        lines = [
            "=" * 42, self.invoice.company.name.center(42),
            f"TPIN: {self.invoice.company.tpin}".center(42), "=" * 42,
            f"Invoice: {self.invoice.invoice_number}",
            f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}",
        ]
        
        # Add Customer Name if it exists
        if self.invoice.customer_name and self.invoice.customer_name != "Cash Customer":
            lines.append(f"Customer: {self.invoice.customer_name}")
            
        lines.append("-" * 42)
        
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
            
        return "\\n".join(lines)
'''

# Overwrite the broken file entirely
file_path.write_text(correct_code.strip(), encoding="utf-8")
print("✅ Successfully rebuilt sales/receipt_service.py with VAT and Customer Name support.")