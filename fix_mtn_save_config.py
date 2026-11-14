import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "payments" / "views.py"

content = views_path.read_text(encoding="utf-8")

# The updated view that saves ALL fields correctly
new_view = '''
@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def payment_configs(request):
    if request.method == "GET":
        configs = BranchPaymentConfig.objects.filter(branch=request.branch)
        return Response([{
            "id": c.id, "provider": c.provider, "merchant_id": c.merchant_id,
            "api_key": c.api_key, "api_secret": c.api_secret,
            "mtn_subscription_key": c.mtn_subscription_key,
            "mtn_api_user": c.mtn_api_user,
            "mtn_api_key": c.mtn_api_key,
            "mtn_target_env": c.mtn_target_env,
            "is_default": c.is_default, "is_enabled": c.is_enabled,
        } for c in configs])
        
    if request.user.user_type not in ("TENANT_OWNER", "ADMIN", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    provider = data.get("provider")
    
    config, created = BranchPaymentConfig.objects.update_or_create(
        branch=request.branch, provider=provider,
        defaults={
            "merchant_id": data.get("merchant_id", ""),
            "api_key": data.get("api_key", ""),
            "api_secret": data.get("api_secret", ""),
            "mtn_subscription_key": data.get("mtn_subscription_key", ""),
            "mtn_api_user": data.get("mtn_api_user", ""),
            "mtn_api_key": data.get("mtn_api_key", ""),
            "mtn_target_env": data.get("mtn_target_env", "sandbox"),
            "is_default": data.get("is_default", False),
            "is_enabled": True,
        },
    )
    
    return Response({"success": True, "id": config.id})
'''

# Replace the old payment_configs view
pattern = r"@api_view\(\[\"GET\", \"POST\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef payment_configs\(request\):.*?return Response\(\{\"success\": True, \"id\": config.id, \"created\": created\}\)"
content = re.sub(pattern, new_view.strip(), content, flags=re.DOTALL)

views_path.write_text(content, encoding="utf-8")
print("✅ Fixed payment_configs view to save MTN fields")