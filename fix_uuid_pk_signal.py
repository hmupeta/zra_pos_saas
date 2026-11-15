"""Fix Branch pre_save signal: use _state.adding instead of 'not instance.pk'."""
import os, sys

SIGNALS = "subscriptions/signals.py"
if not os.path.exists(SIGNALS):
    print(f"❌ {SIGNALS} not found — run from project root"); sys.exit(1)

with open(SIGNALS, "r", encoding="utf-8") as f:
    content = f.read()

# --- Fix branch signal ---
branch_old = (
    "@receiver(pre_save, sender=Branch)\n"
    "def enforce_branch_limit(sender, instance, **kwargs):\n"
    "    if not instance.pk:"
)
branch_new = (
    "@receiver(pre_save, sender=Branch)\n"
    "def enforce_branch_limit(sender, instance, **kwargs):\n"
    "    # NOTE: Branch uses UUID pk with a default, so instance.pk is populated\n"
    "    # BEFORE save. Use _state.adding to detect unsaved instances reliably.\n"
    "    if instance._state.adding:"
)

if branch_old in content:
    content = content.replace(branch_old, branch_new)
    print("✅ Fixed Branch pre_save signal")
elif "if instance._state.adding:" in content:
    print("ℹ️  Branch signal already fixed — nothing to do")
else:
    print("❌ Could not locate Branch signal block — inspect manually")

# --- Fix User signal for consistency (defensive) ---
user_old = (
    "@receiver(pre_save, sender=User)\n"
    "def enforce_user_limit(sender, instance, **kwargs):\n"
    "    if instance.pk:\n"
    "        return  # only enforce on creation"
)
user_new = (
    "@receiver(pre_save, sender=User)\n"
    "def enforce_user_limit(sender, instance, **kwargs):\n"
    "    if not instance._state.adding:\n"
    "        return  # only enforce on creation"
)

if user_old in content:
    content = content.replace(user_old, user_new)
    print("✅ Fixed User pre_save signal (also using _state.adding now)")
elif "if not instance._state.adding:" in content:
    print("ℹ️  User signal already fixed")

with open(SIGNALS, "w", encoding="utf-8") as f:
    f.write(content)
print(f"\n💾 Saved {SIGNALS}")
print("⚠️  Restart any running Django server to reload the signal.")