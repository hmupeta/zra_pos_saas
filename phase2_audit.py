"""Phase 2B: audit ZRA / sales / accounting state."""
import os, sys, json
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django; django.setup()

from django.apps import apps
from django.db import connection

report = {"models": {}, "zra_checks": {}, "notes": []}

# ── 1. Model inventory ──────────────────────────────────────────────────
for label in ("inventory", "sales", "zra_integration", "accounting", "payments", "customers"):
    try:
        app = apps.get_app_config(label)
    except LookupError:
        report["models"][label] = "APP MISSING"
        continue
    models_list = []
    for m in app.get_models():
        try:
            count = m.objects.count()
        except Exception:
            count = "?"
        models_list.append({"model": m.__name__, "rows": count,
                            "fields": [f.name for f in m._meta.fields]})
    report["models"][label] = models_list

# ── 2. ZRA compliance checks ────────────────────────────────────────────
try:
    Invoice = apps.get_model("sales", "Invoice")
    inv_fields = {f.name for f in Invoice._meta.fields}
    report["zra_checks"]["invoice_has_zra_receipt"] = any(
        k in inv_fields for k in ("zra_receipt_no", "zra_signature", "zra_submitted_at")
    )
    report["zra_checks"]["invoice_has_zra_status"] = any(
        k in inv_fields for k in ("zra_status", "fiscal_status")
    )
    report["zra_checks"]["invoice_fields"] = sorted(inv_fields)
except LookupError:
    report["notes"].append("sales.Invoice not found")

try:
    Shift = apps.get_model("sales", "Shift")
    shift_fields = {f.name for f in Shift._meta.fields}
    report["zra_checks"]["shift_has_zreport"] = any(
        k in shift_fields for k in ("zreport_number", "zreport_submitted_at", "zra_zreport")
    )
    report["zra_checks"]["shift_fields"] = sorted(shift_fields)
except LookupError:
    report["notes"].append("sales.Shift not found")

# ── 3. Look for VSDC service ────────────────────────────────────────────
vsdc_candidates = []
for base in ("zra_integration", "sales", "payments"):
    d = os.path.join(base)
    if not os.path.isdir(d):
        continue
    for fname in os.listdir(d):
        if not fname.endswith(".py"):
            continue
        p = os.path.join(d, fname)
        try:
            src = open(p, encoding="utf-8").read()
        except Exception:
            continue
        if any(k in src for k in ("VSDC", "vsdc", "vSdc", "smartInvoice",
                                  "smart_invoice", "SubmitInvoice", "ZRA_", "zra_api")):
            vsdc_candidates.append(p)
report["zra_checks"]["vsdc_files"] = vsdc_candidates

# ── 4. Plan features snapshot ───────────────────────────────────────────
try:
    Plan = apps.get_model("subscriptions", "Plan")
    report["plans"] = [
        {"name": p.name,
         "max_branches": p.max_branches,
         "max_users": p.max_users,
         "features": {f: getattr(p, f) for f in (
             "has_pos", "has_inventory", "has_zra_smart_invoice",
             "has_full_accounting", "has_multi_branch_reports",
             "has_api_access", "has_dedicated_manager", "has_custom_sla",
         )}}
        for p in Plan.objects.all()
    ]
except Exception as e:
    report["notes"].append(f"Plan audit failed: {e}")

# ── 5. Print + save ─────────────────────────────────────────────────────
def pp_header(t): print("\n" + "=" * 62 + "\n" + t + "\n" + "=" * 62)

pp_header("📊 MODEL ROW COUNTS")
for app, items in report["models"].items():
    if isinstance(items, str):
        print(f"  {app}: {items}"); continue
    print(f"  {app}:")
    for m in items:
        print(f"    • {m['model']:30s} {m['rows']:>6} rows")

pp_header("🛡️  ZRA COMPLIANCE")
for k, v in report["zra_checks"].items():
    if k.endswith("_fields"):
        print(f"  {k}: {', '.join(v) if v else '(none)'}")
    elif k == "vsdc_files":
        print(f"  VSDC-related files found: {len(v)}")
        for f in v: print(f"    - {f}")
    else:
        print(f"  {k}: {'✅' if v else '❌'}")

pp_header("💳 PLAN FEATURES")
for p in report.get("plans", []):
    print(f"  {p['name']:<14} branches={p['max_branches']:<4} users={p['max_users']:<4}")
    on = [k for k, v in p["features"].items() if v]
    print(f"      ON: {', '.join(on) or '(none)'}")

if report["notes"]:
    pp_header("📝 NOTES")
    for n in report["notes"]: print(f"  • {n}")

out = "phase2_audit.json"
with open(out, "w") as f:
    json.dump(report, f, indent=2, default=str)
print(f"\n💾 Full report → {out}")
print("👉 Please share this file (or its console output) with your engineering lead.")