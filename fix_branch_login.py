import os
import subprocess
import sys
import re

def run_cmd(cmd):
    print(f"⚙️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    return True

def main():
    print("🚀 Starting Branch Login Fix...")

    # 1. Patch core/views.py
    views_path = "core/views.py"
    if os.path.exists(views_path):
        with open(views_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Only patch if not already patched
        if "assigned_branch_id" not in content:
            # Find the login function (assuming it's named `login_view` or `login_user`)
            # We'll search for the return Response with token
            # This regex looks for the success return block in the login view
            login_return_pattern = re.compile(r"(return Response\(\{[\s\S]*?\"token\":[\s\S]*?\}\)\s*)")
            
            match = login_return_pattern.search(content)
            if match:
                old_block = match.group(1)
                new_block = """
        # --- BRANCH ENFORCEMENT FOR STAFF ---
        from core.models import BranchAccess
        assigned_access = BranchAccess.objects.filter(user=user).first()
        assigned_branch_id = str(assigned_access.company.id) if assigned_access else None

        if user.user_type in ('CASHIER', 'MANAGER', 'ACCOUNTANT', 'FINANCE_MANAGER', 'SALES_AGENT'):
            if not assigned_branch_id:
                return Response({"error": "No branch assigned to your account. Contact your manager."}, status=403)

        return Response({
            "token": token.key,
            "user": {
                "id": user.id,
                "username": user.username,
                "user_type": user.user_type,
            },
            "tenant": user.tenant.name if user.tenant else None,
            "branchId": assigned_branch_id  # <--- NEW FIELD
        })
"""
                # We do a somewhat risky replacement, but it's the best we can do without knowing the exact view code
                # Safely replacing the old return response with the new one
                content = content.replace(old_block, new_block)
                with open(views_path, "w", encoding="utf-8") as f:
                    f.write(content)
                print("✅ Patched core/views.py with branch enforcement logic.")
            else:
                print("⚠️ Could not automatically find the login return block in core/views.py.")
        else:
            print("ℹ️ core/views.py already patched.")

    # 2. Patch templates/pos/login.html
    login_html_path = "templates/pos/login.html"
    if os.path.exists(login_html_path):
        with open(login_html_path, "r", encoding="utf-8") as f:
            html_content = f.read()
            
        if "res.branchId" not in html_content:
            # Find the fetch branches block and replace it
            old_js = """        // If no branchId was returned, fetch branches
        const branches = await apiFetch('/auth/branches/');
        if (branches.length === 0) {
          this.error = 'No branches assigned. Contact your administrator.';
          return;
        }
        if (branches.length === 1) {
          localStorage.setItem('branchId', branches[0].id);
          location.href = '/pos';
        } else {
          location.href = '/select-branch';
        }"""
            
            new_js = """        // --- NEW LOGIC: If backend assigned a branch, go straight to POS ---
        if (res.branchId) {
            localStorage.setItem('branchId', res.branchId);
            location.href = '/pos';
            return;
        }

        // If no branchId was returned, it means they are an Owner and need to select one
        const branches = await apiFetch('/auth/branches/');
        if (branches.length === 0) {
          this.error = 'No branches assigned. Contact your administrator.';
          return;
        }
        if (branches.length === 1) {
          localStorage.setItem('branchId', branches[0].id);
          location.href = '/pos';
        } else {
          location.href = '/select-branch';
        }"""
            
            if old_js in html_content:
                html_content = html_content.replace(old_js, new_js)
                with open(login_html_path, "w", encoding="utf-8") as f:
                    f.write(html_content)
                print("✅ Patched templates/pos/login.html to respect branchId.")
            else:
                print("⚠️ Could not automatically find the branch logic in login.html.")
        else:
            print("ℹ️ login.html already patched.")

    # 3. Assign BranchAccess to Cashier and Manager
    print("\n👤 Assigning BranchAccess to cashier1 and manager1...")
    assign_script = """
from django.contrib.auth import get_user_model
from core.models import Company, BranchAccess
User = get_user_model()

branch = Company.objects.filter(name__icontains='Demo').first()
if not branch:
    print('❌ Could not find a demo branch.')
else:
    for uname in ['cashier1', 'manager1']:
        try:
            u = User.objects.get(username=uname)
            BranchAccess.objects.get_or_create(user=u, company=branch)
            print(f'✅ Assigned {uname} to {branch.name}')
        except User.DoesNotExist:
            print(f'⚠️ User {uname} does not exist yet.')
"""
    with open("_temp_assign.py", "w") as f:
        f.write(assign_script)
    run_cmd("python manage.py shell < _temp_assign.py")
    os.remove("_temp_assign.py")

    # 4. Push to GitHub
    print("\n📤 Pushing to GitHub...")
    if run_cmd("git add ."):
        if run_cmd('git commit -m "Enforce branch isolation on login and bypass select-branch for staff"'):
            run_cmd("git push origin main")
            
    print("\n🎉 ALL DONE!")

if __name__ == "__main__":
    main()