import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "inventory" / "views.py"

content = views_path.read_text(encoding="utf-8")

# The complete, correct category view supporting GET, POST, and PUT
new_view = '''
@api_view(["GET", "POST", "PUT"])
@permission_classes([IsAuthenticated])
def categories_list(request):
    if request.method == "GET":
        cats = Category.objects.filter(tenant=request.tenant)
        return Response([{
            "id": c.id, "name": c.name, "zra_item_code": c.zra_item_code, "is_active": c.is_active
        } for c in cats])
        
    if request.user.user_type not in ("TENANT_OWNER", "MANAGER"):
        return Response({"error": "Insufficient permissions"}, status=403)

    data = request.data
    
    if request.method == "POST":
        c = Category.objects.create(
            tenant=request.tenant, name=data["name"], 
            zra_item_code=data.get("zra_item_code", "")
        )
        return Response({"success": True, "id": c.id}, status=201)
        
    elif request.method == "PUT":
        try:
            c = Category.objects.get(id=data["id"], tenant=request.tenant)
            c.name = data.get("name", c.name)
            c.zra_item_code = data.get("zra_item_code", c.zra_item_code)
            c.is_active = data.get("is_active", c.is_active)
            c.save()
            return Response({"success": True})
        except Category.DoesNotExist:
            return Response({"error": "Not found"}, status=404)
'''

# Regex to find the existing categories_list view and replace it
pattern = r"@api_view\(\[\"GET\", \"POST\"\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef categories_list\(request\):.*?return Response\(\{\"success\": True, \"id\": c\.id\}, status=201\)"

if re.search(pattern, content, flags=re.DOTALL):
    content = re.sub(pattern, new_view.strip(), content, flags=re.DOTALL)
    views_path.write_text(content, encoding="utf-8")
    print("✅ Updated categories_list to support PUT (Edit).")
else:
    print("⚠️ Could not find exact match. Checking for variations...")
    # Fallback: if the view signature is slightly different
    pattern_fallback = r"@api_view\(\['GET', 'POST'\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef categories_list\(request\):.*?status=201\)"
    if re.search(pattern_fallback, content, flags=re.DOTALL):
        content = re.sub(pattern_fallback, new_view.strip(), content, flags=re.DOTALL)
        views_path.write_text(content, encoding="utf-8")
        print("✅ Updated using fallback pattern.")
    else:
        print("❌ Could not automatically fix. Please check inventory/views.py manually.")

print("\n🎉 Done! Restart the server and try editing a category again.")