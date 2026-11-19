import subprocess
import sys
import os

def run_cmd(cmd):
    print(f"⚙️ Running: {cmd}")
    result = subprocess.run(cmd, shell=True, text=True, capture_output=True)
    if result.returncode != 0:
        print(f"❌ Error: {result.stderr}")
        return False
    print(result.stdout)
    return True

def main():
    print("🚀 Pushing Phase 2 enhancements to Git...\n")
    
    # 1. Verify we are in a git repo
    if not os.path.exists(".git"):
        print("❌ Not a git repository. Run from project root.")
        sys.exit(1)
    
    # 2. Stage all changes
    if not run_cmd("git add ."):
        sys.exit(1)
    
    # 3. Check if there's anything to commit
    status = subprocess.run("git status --porcelain", shell=True, text=True, capture_output=True)
    if not status.stdout.strip():
        print("ℹ️  No changes to commit. Everything is already up to date.")
        return
    
    # 4. Commit with a descriptive message
    commit_msg = """Phase 2: Invoice detail page, offline ZRA queue, dashboard fixes

- Add invoice_detail API and template for viewing invoice line items
- Fix duplicate product cleanup and image re-attachment
- Fix ZRA offline fallback in CartService.checkout
- Add get_safe_tenant_branch fallback to reports/views.py dashboard
- Fix missing SalesTarget and InvoiceItem imports in sales/views.py
- Add sales/scan-add/ URL route
- Hide product edit/stock buttons from cashier role
"""
    
    # Escape the message for Windows
    commit_msg = commit_msg.replace('"', '\\"').replace('\n', '\\n')
    
    if not run_cmd(f'git commit -m "{commit_msg}"'):
        print("⚠️  Commit failed. Maybe there's nothing to commit or a hook blocked it.")
        # Don't exit here, maybe there's a stale commit we can push
    
    # 5. Push to GitHub
    if not run_cmd("git push origin main"):
        print("⚠️  Push failed. Check your network and GitHub credentials.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Successfully pushed to GitHub!")
    print("=" * 60)
    print("\nRender will auto-deploy if you've connected the repo.")
    print("Otherwise, trigger a manual deploy from the Render dashboard.")

if __name__ == "__main__":
    main()