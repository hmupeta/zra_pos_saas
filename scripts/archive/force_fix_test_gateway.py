import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "payments" / "views.py"

content = views_path.read_text(encoding="utf-8")

# The exact new function we want
new_function = '''
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def test_gateway_connection(request):
    provider = request.data.get("provider")
    
    # We query the DB directly to avoid any signature mismatch errors
    config = BranchPaymentConfig.objects.filter(branch=request.branch, provider=provider).first()
    
    if not config:
        return Response({"error": "Configuration not found for this branch"}, status=404)

    if provider == "MTN_DIRECT":
        service = MTNMoMoService(config)
        token = service.get_access_token()
        if token:
            return Response({"success": True, "message": "Successfully authenticated with MTN MoMo!"})
        else:
            return Response({"error": "Failed to authenticate. Check your Subscription Key, API User, and API Key."}, status=400)
            
    elif provider == "STRIPE":
        import requests
        if not config.api_key:
            return Response({"error": "Stripe API Key is missing"}, status=400)
        headers = {"Authorization": f"Bearer {config.api_key}"}
        res = requests.get("https://api.stripe.com/v1/balance", headers=headers)
        if res.status_code == 200:
            return Response({"success": True, "message": "Successfully connected to Stripe!"})
        return Response({"error": "Stripe authentication failed. Check your Secret Key."}, status=400)

    return Response({"success": True, "message": f"Basic config check passed for {provider}."})
'''

# Use regex to find the entire function block and replace it
pattern = r"@api_view\(\[\"POST\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef test_gateway_connection\(request\):.*?return Response\(\{\"success\": True, \"message\": f\"Basic config check passed for \{provider\}\.\"\}\)"

if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_function.strip(), content, flags=re.DOTALL)
    views_path.write_text(content, encoding="utf-8")
    print("✅ Successfully overwrote test_gateway_connection function.")
else:
    # Fallback if regex fails (just in case the file was modified)
    print("⚠️ Could not find the exact function block. Forcing a manual replacement.")
    old_buggy_line = "config = BranchPaymentConfig.resolve_for_branch(request.branch, provider)"
    new_fixed_line = "config = BranchPaymentConfig.objects.filter(branch=request.branch, provider=provider).first()"
    if old_buggy_line in content:
        content = content.replace(old_buggy_line, new_fixed_line)
        views_path.write_text(content, encoding="utf-8")
        print("✅ Replaced the specific buggy line.")
    else:
        print("❌ Could not find the buggy line. Please check payments/views.py manually.")

print("\n🎉 Done! Restart your server and test the gateway again.")