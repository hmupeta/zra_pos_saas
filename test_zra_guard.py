"""Prove the ZRA guard actually fires on real data."""
import os, sys
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()

from django.core.exceptions import ValidationError
from django.utils import timezone
from sales.models import Invoice, Shift

shift = Shift.objects.filter(is_closed=False).first() or Shift.objects.first()
if not shift:
    print("❌ No shift exists — create one via UI first"); sys.exit(1)

inv = Invoice.objects.create(
    invoice_number=f"TESTSIG-{timezone.now().strftime('%H%M%S')}",
    tenant=shift.tenant, company=shift.company, shift=shift,
    cashier=shift.cashier, customer_name="Test Customer",
    subtotal=100, tax_total=16, total=116,
    status="PENDING", zra_status="PENDING",
)
print(f"✅ Created test invoice #{inv.invoice_number}\n")

results = []

# A: PAID without fiscalization → BLOCKED
try:
    inv.status = "PAID"; inv.zra_status = "PENDING"; inv.save()
    results.append(("A: PAID w/o fiscalization", "FAIL — allowed"))
except ValidationError:
    results.append(("A: PAID w/o fiscalization", "PASS — blocked"))
    inv.refresh_from_db()

# B: PAID + OFFLINE_QUEUED → ALLOWED
try:
    inv.status = "PAID"; inv.zra_status = "OFFLINE_QUEUED"; inv.save()
    results.append(("B: PAID + OFFLINE_QUEUED", "PASS — allowed"))
except ValidationError as e:
    results.append(("B: PAID + OFFLINE_QUEUED", f"FAIL — {e}"))

# C: SUBMITTED without receipt → BLOCKED
inv.refresh_from_db()
inv.status = "PENDING"; inv.zra_status = "SUBMITTED"; inv.zra_receipt_number = ""
try:
    inv.save()
    results.append(("C: SUBMITTED w/o receipt", "FAIL — allowed"))
except ValidationError:
    results.append(("C: SUBMITTED w/o receipt", "PASS — blocked"))

# D: PAID + SUBMITTED + receipt → ALLOWED
inv.refresh_from_db()
inv.status = "PAID"; inv.zra_status = "SUBMITTED"; inv.zra_receipt_number = "RCPT-TEST-001"
try:
    inv.save()
    results.append(("D: PAID + SUBMITTED + receipt", "PASS — allowed"))
except ValidationError as e:
    results.append(("D: PAID + SUBMITTED + receipt", f"FAIL — {e}"))

inv.delete()
print("🧹 Cleaned up test invoice\n")
print("=" * 62); print("RESULTS"); print("=" * 62)
failed = 0
for name, result in results:
    ok = result.startswith("PASS")
    print(f"{'✅' if ok else '❌'} {name}: {result}")
    if not ok: failed += 1
print("\n" + ("🎉 ZRA guard verified" if failed == 0 else f"❌ {failed} test(s) failed"))