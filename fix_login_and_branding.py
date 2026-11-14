import os
import re
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent

# 1. Fix the core views to fetch branches directly from the DB
views_path = BACKEND_PATH / "core" / "views.py"
with open(views_path, "r", encoding="utf-8") as f:
    views_content = f.read()

# Replace branches_list
views_content = re.sub(
    r"@api_view\(\['GET'\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef branches_list\(request\):.*?return Response\(\[.*?\]\)",
    """@api_view(['GET'])
@permission_classes([IsAuthenticated])
def branches_list(request):
    from core.models import BranchAccess
    qs = BranchAccess.objects.filter(user=request.user, company__is_active=True).select_related("company")
    return Response([{
        "id": ba.company.id, 
        "name": ba.company.name, 
        "code": ba.company.branch_code, 
        "tpin": ba.company.tpin,
    } for ba in qs])""",
    views_content,
    flags=re.DOTALL
)

# Replace switch_branch to check the DB directly instead of middleware
views_content = re.sub(
    r"@api_view\(\['POST'\]\)\n@permission_classes\(\[IsAuthenticated\]\)\ndef switch_branch\(request\):.*?return Response\(\{\"success\": True, \"branch_id\": branch.id, \"branch_name\": branch.name\}\)",
    """@api_view(['POST'])
@permission_classes([IsAuthenticated])
def switch_branch(request):
    branch_id = request.data.get("branch_id")
    try:
        branch = Company.objects.get(pk=branch_id, tenant=request.user.tenant)
    except Company.DoesNotExist:
        return Response({"error": "Branch not found"}, status=404)
        
    has_access = request.user.branch_access.filter(company=branch).exists()
    if not has_access and request.user.user_type not in ("SUPER_ADMIN", "TENANT_OWNER", "ADMIN"):
        return Response({"error": "No access"}, status=403)
        
    request.session["branch_id"] = branch.id
    return Response({"success": True, "branch_id": branch.id, "branch_name": branch.name})""",
    views_content,
    flags=re.DOTALL
)

with open(views_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(views_content)

print("✅ Patched core/views.py to fix branch fetching.")

# 2. Change the title in base.html
base_path = BACKEND_PATH / "templates" / "pos" / "base.html"
with open(base_path, "r", encoding="utf-8") as f:
    base_content = f.read()

base_content = base_content.replace(
    "<title>{% block title %}POS{% endblock %}</title>",
    "<title>{% block title %}Nimbus POS{% endblock %}</title>"
)

with open(base_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(base_content)

# 3. Change the title in login.html
login_path = BACKEND_PATH / "templates" / "pos" / "login.html"
with open(login_path, "r", encoding="utf-8") as f:
    login_content = f.read()

login_content = login_content.replace(
    "{% block title %}Login · POS{% endblock %}",
    "{% block title %}Nimbus POS Login{% endblock %}"
)
login_content = login_content.replace(
    '<h1 class="text-3xl font-bold text-brand-700">POS Login</h1>',
    '<h1 class="text-3xl font-bold text-brand-700">Nimbus POS Login</h1>'
)

with open(login_path, "w", encoding="utf-8", newline="\n") as f:
    f.write(login_content)

print("✅ Patched templates to say 'Nimbus POS'.")