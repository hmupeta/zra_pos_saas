import os
import subprocess
import sys
import time

def run_cmd(cmd):
    print(f"⚙️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Error executing: {cmd}")
        print(result.stderr)
        sys.exit(1)
    return result.stdout

def write_file(path, content):
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"📝 Created/Updated: {path}")

def main():
    print("🚀 Starting Auto-Fix and Deploy Process...")

    # --- 1. Create patch_branch.py ---
    patch_script = """import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'pos_backend.settings')
django.setup()

from django.contrib.auth import get_user_model
from core.models import Company

User = get_user_model()

def run():
    print("Starting branch patch...")
    company = Company.objects.first()
    if not company:
        print("No company found in DB!")
        return

    print(f"Found Company: {company.name} (ID: {company.id})")

    users = User.objects.all()
    for u in users:
        u.company = company
        u.save()
        print(f"Assigned user {u.username} to {company.name}")
        
    print("Patch complete!")

if __name__ == "__main__":
    run()
"""
    write_file("patch_branch.py", patch_script)

    # --- 2. Update urls.py to include the patch trigger ---
    urls_path = "pos_backend/urls.py"
    with open(urls_path, "r", encoding="utf-8") as f:
        urls_content = f.read()

    if "run_patch" not in urls_content:
        # Add the patch view function
        patch_view = """
from django.http import HttpResponse
import subprocess
import sys

def run_patch(request):
    if os.environ.get('RENDER') != 'true':
        return HttpResponse("Only works in production")
    result = subprocess.run([sys.executable, 'patch_branch.py'], capture_output=True, text=True)
    return HttpResponse(f"<h1>Patch Result</h1><pre>{result.stdout}</pre>")

# --- TEMP TRIGGERS ---
"""
        urls_content = urls_content.replace("urlpatterns = [", patch_view + "urlpatterns = [")
        urls_content = urls_content.replace("urlpatterns = [", "urlpatterns = [\n    path('trigger-patch/', run_patch),")
        
        write_file(urls_path, urls_content)

    # --- 3. Push to GitHub ---
    print("\n📤 Pushing to GitHub...")
    run_cmd("git add patch_branch.py pos_backend/urls.py")
    run_cmd('git commit -m "Auto-fix: Add trigger to assign users to company"')
    run_cmd("git push origin main")

    print("\n✅ GitHub push successful!")
    print("⏳ Waiting 90 seconds for Render to finish deploying...")
    time.sleep(90)

    # --- 4. Trigger the patch on Render ---
    print("\n🌐 Triggering the patch on Render...")
    # Note: Windows PowerShell requires curl.exe
    url = "https://zra-pos-saas.onrender.com/trigger-patch/"
    try:
        response = subprocess.run(["curl", "-s", url], capture_output=True, text=True)
        if "Patch complete!" in response.stdout or "Assigned user" in response.stdout:
            print("✅ Patch applied successfully on Render!")
        else:
            print("⚠️ Could not confirm patch success. Check the URL manually:")
            print(url)
    except Exception as e:
        print(f"⚠️ Could not trigger patch automatically: {e}")

    # --- 5. Clean up the security hole ---
    print("\n🧹 Cleaning up the temporary trigger URLs...")
    with open(urls_path, "r", encoding="utf-8") as f:
        urls_content = f.read()

    # Remove the patch path
    urls_content = urls_content.replace("    path('trigger-patch/', run_patch),\n", "")
    
    # Remove the run_patch function
    import re
    urls_content = re.sub(r"def run_patch\(request\):.*?# --- TEMP TRIGGERS ---\n", "", urls_content, flags=re.DOTALL)

    write_file(urls_path, urls_content)

    print("\n📤 Pushing cleanup to GitHub...")
    run_cmd("git add pos_backend/urls.py")
    run_cmd('git commit -m "SECURITY: Remove temporary patch trigger"')
    run_cmd("git push origin main")

    print("\n🎉 ALL DONE!")
    print("Wait 90 seconds for Render to finish the final deploy, then log in with demo_owner / Demo@123456")

if __name__ == "__main__":
    main()