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
    print("🚀 Pushing Privacy Policy to Git...\n")
    
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
        print("ℹ️  No changes to commit.")
        return
    
    # 4. Commit
    commit_msg = "Add Zambia-compliant Privacy Policy page and footer link"
    if not run_cmd(f'git commit -m "{commit_msg}"'):
        print("⚠️  Commit failed.")
        sys.exit(1)
    
    # 5. Push
    if not run_cmd("git push origin main"):
        print("⚠️  Push failed. Check your credentials.")
        sys.exit(1)
    
    print("\n" + "=" * 60)
    print("🎉 Privacy Policy pushed successfully!")
    print("=" * 60)
    print("Render will auto-deploy if connected.")

if __name__ == "__main__":
    main()