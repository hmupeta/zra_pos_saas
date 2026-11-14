import os
from pathlib import Path

BACKEND_PATH = Path(__file__).resolve().parent
views_path = BACKEND_PATH / "inventory" / "views.py"

content = views_path.read_text(encoding="utf-8")

# Remove the dangerous 'image_url' return that causes the crash
old_return = '''            p.save()
            return Response({"success": True, "id": p.id, "image_url": p.image.url if p.image else None})'''
new_return = '''            p.save()
            return Response({"success": True, "id": p.id})'''

if old_return in content:
    content = content.replace(old_return, new_return)
    views_path.write_text(content, encoding="utf-8")
    print("✅ Fixed backend response (removed unsafe image.url access).")
else:
    print("⚠️ Could not find the exact return statement. Checking for variations...")
    # Fallback just in case spacing is different
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'return Response({"success": True, "id": p.id, "image_url": p.image.url' in line:
            lines[i] = '            return Response({"success": True, "id": p.id})'
            print("✅ Fixed backend response using line search.")
            break
    views_path.write_text('\n'.join(lines), encoding="utf-8")

print("\n🎉 Done! Restart the server and try saving the image again.")