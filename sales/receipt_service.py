class ReceiptService:
    ESC, GS = "\x1b", "\x1d"

    def __init__(self, invoice):
        self.invoice = invoice

    def to_escpos(self, width=80):
        cpl = 32 if width == 58 else 42
        company = self.invoice.company
        
        lines = [self.ESC + "@", self.ESC + "a\x01"] # Init & Center
        
        # Company Header
        lines.append(company.name + "\n")
        if company.address:
            lines.append(company.address[:cpl] + "\n")
        if company.phone:
            lines.append(f"Tel: {company.phone}\n")
        lines.append(f"TPIN: {company.tpin}\n")
        lines.append("-" * cpl + "\n")
        
        # Invoice Details
        lines.append(self.ESC + "a\x00") # Left align
        lines.append(f"Invoice: {self.invoice.invoice_number}\n")
        lines.append(f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}\n")
        
        # Customer Details
        if self.invoice.customer_name and self.invoice.customer_name != "Cash Customer":
            lines.append(f"Customer: {self.invoice.customer_name}\n")
        if self.invoice.customer_phone:
            lines.append(f"Phone: {self.invoice.customer_phone}\n")
            
        lines.append("-" * cpl + "\n")
        
        # Items
        for item in self.invoice.items.all():
            name = item.product.name[:18]
            lines.append(f"{name:<20}{int(item.quantity):>3}{float(item.unit_price):>6.2f}{float(item.total):>8.2f}\n")
            
        lines.extend([
            "-" * cpl + "\n",
            f"{'Subtotal:':<25}K{float(self.invoice.subtotal):>10.2f}\n",
            f"{'VAT (16%):':<25}K{float(self.invoice.tax_total):>10.2f}\n",
        ])
        
        if getattr(self.invoice, 'discount_total', 0) > 0:
            lines.append(f"{'Discount:':<25}K{-float(self.invoice.discount_total):>10.2f}\n")
            
        lines.extend([
            "-" * cpl + "\n",
            self.ESC + "!\x10",
            f"{'TOTAL:':<25}K{float(self.invoice.total):>10.2f}\n",
            self.ESC + "!\x00",
            "-" * cpl + "\n",
        ])
        
        if self.invoice.zra_validation_code:
            lines.append(self.ESC + "a\x01")
            lines.append("ZRA SMART INVOICE\n")
            lines.append(f"Code: {self.invoice.zra_validation_code}\n")
            lines.append(self.ESC + "a\x00")
            
        lines.append("\n")
        lines.append(self.ESC + "a\x01")
        lines.append("Thank you for your business!\n")
        lines.append("\n\n\n")
        lines.append(self.GS + "V\x42\x00")
        
        return "".join(lines).encode("latin-1", errors="replace")

    def to_text(self):
        company = self.invoice.company
        
        lines = [
            "=" * 42, 
            company.name.center(42)
        ]
        
        if company.address:
            lines.append(company.address[:42].center(42))
        if company.phone:
            lines.append(f"Tel: {company.phone}".center(42))
            
        lines.append(f"TPIN: {company.tpin}".center(42))
        lines.append("=" * 42)
        
        lines.extend([
            f"Invoice: {self.invoice.invoice_number}",
            f"Date: {self.invoice.created_at.strftime('%Y-%m-%d %H:%M')}"
        ])
        
        if self.invoice.customer_name and self.invoice.customer_name != "Cash Customer":
            lines.append(f"Customer: {self.invoice.customer_name}")
        if self.invoice.customer_phone:
            lines.append(f"Phone: {self.invoice.customer_phone}")
            
        lines.append("-" * 42)
        
        for item in self.invoice.items.all():
            lines.append(f"{item.product.name[:25]:<28}{float(item.quantity):>4.0f} x {float(item.unit_price):>7.2f} = {float(item.total):>8.2f}")
        
        lines.extend([
            "", 
            "-" * 42, 
            f"{'Subtotal:':<28}K{float(self.invoice.subtotal):>10.2f}",
            f"{'VAT (16%):':<28}K{float(self.invoice.tax_total):>10.2f}",
        ])
        
        if getattr(self.invoice, 'discount_total', 0) > 0:
            lines.append(f"{'Discount:':<28}K{-float(self.invoice.discount_total):>10.2f}")
            
        lines.extend([
            f"{'TOTAL:':<28}K{float(self.invoice.total):>10.2f}", 
            "=" * 42
        ])
        
        if self.invoice.zra_validation_code:
            lines.append(f"ZRA Code: {self.invoice.zra_validation_code}")
            
        return "\n".join(lines)