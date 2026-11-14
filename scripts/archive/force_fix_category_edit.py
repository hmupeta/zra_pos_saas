import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "inventory" / "views.py"

content = views_path.read_text(encoding="utf-8")

# The new, perfect view function
new_view_block = '''@api_view(["GET", "POST", "PUT"])
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

# Find the start of the current function
start_idx = content.find("def categories_list(request):")
if start_idx == -1:
    print("❌ Could not find categories_list at all.")
else:
    # Find the start of the decorator (the line above the function)
    decorator_idx = content.rfind("@api_view", 0, start_idx)
    if decorator_idx == -1:
        decorator_idx = start_idx
    
    # Find the end of the function (the next @api_view or end of file)
    end_idx = content.find("@api_view", start_idx)
    if end_idx == -1:
        end_idx = len(content)
    else:
        # We need to backtrack from the next @api_view to remove any extra blank lines or previous function's end
        # But to be safe, we'll just replace up to the next @api_view, and then append the next @api_view.
        pass

    # Reconstruct the file
    new_content = content[:decorator_idx] + new_view_block + "\n\n" + content[end_idx:]
    
    views_path.write_text(new_content, encoding="utf-8")
    print("✅ Forcefully replaced the categories_list function.")
    print("🎉 Done! Restart the server and try editing a category again.")