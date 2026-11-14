import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# ============================================================
# 1. Update accounting/signals.py to handle both Cash and Credit
# ============================================================
signals_path = BACKEND_PATH / "accounting" / "signals.py"
signals_code = '''
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from sales.models import Invoice
from .models import Account, Journal, JournalLine

@receiver(post_save, sender=Invoice)
def auto_post_sale_journal(sender, instance, created, **kwargs):
    if instance.status != "PAID":
        return
        
    # If a journal already exists for this invoice, do nothing
    if instance.journals.filter(status="POSTED").exists():
        return
        
    tenant = instance.shift.company.tenant
    if not tenant:
        return
        
    # Determine if it's a Cash sale or Credit (AR) sale
    debit_code = "1100" if instance.payment_method == "CREDIT" else "1000"
    
    debit_acct = Account.objects.filter(tenant=tenant, code=debit_code).first()
    sales_acct = Account.objects.filter(tenant=tenant, code="4000").first()
    vat_acct = Account.objects.filter(tenant=tenant, code="2100").first()

    if not all([debit_acct, sales_acct, vat_acct]):
        return

    try:
        journal = Journal.objects.create(
            tenant=tenant, company=instance.company,
            journal_number=f"JV-{instance.invoice_number}",
            date=instance.created_at.date(),
            description=f"Sale {instance.invoice_number}",
            journal_type="SALES", status="POSTED",
            source_invoice=instance, created_by=instance.cashier,
        )
        
        # Debit Cash or AR
        JournalLine.objects.create(journal=journal, account=debit_acct, debit=instance.total)
        
        # Credit Sales
        JournalLine.objects.create(journal=journal, account=sales_acct, credit=instance.subtotal)
        
        # Credit VAT
        if instance.tax_total > 0:
            JournalLine.objects.create(journal=journal, account=vat_acct, credit=instance.tax_total)
            
    except Exception as e:
        print(f"[WARN] Could not create auto-journal: {e}")
'''
signals_path.write_text(signals_code.strip(), encoding="utf-8")
print("✅ Updated accounting/signals.py to handle both Cash and Credit safely.")

# ============================================================
# 2. Remove manual journal creation from cart_service.py
# ============================================================
cart_file = BACKEND_PATH / "sales" / "cart_service.py"
content = cart_file.read_text(encoding="utf-8")

# Find the manual journal block and remove it
pattern = r"        # Post Accounting \(AR instead of Cash for Credit\).*?JournalLine\.objects\.create\(journal=journal, account=vat_acct, credit=invoice\.tax_total\)"

if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, "        # (Accounting Journal is automatically created by the signal in accounting/signals.py)", content, flags=re.DOTALL)
    cart_file.write_text(content, encoding="utf-8")
    print("✅ Removed duplicate manual journal creation from cart_service.py")
else:
    print("⚠️ Could not find the manual journal block. (It might have been removed already).")

print("\n🎉 Done! Restart the server and try checking out.")