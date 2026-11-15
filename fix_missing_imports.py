"""Fix missing 'requires_plan_feature' imports in gated files.

Uses Python's AST to find the correct insertion point (after all real
imports, or after the module docstring if there are no imports).
"""
import os, sys, ast, py_compile

if not os.path.exists("manage.py"):
    print("❌ Run from project root"); sys.exit(1)

IMPORT_LINE = "from subscriptions.permissions import requires_plan_feature"
TARGETS = ["accounting/views.py", "reports/views.py"]


def diagnose(path):
    print(f"\n📄 {path}")
    if not os.path.exists(path):
        print(f"  ⚠️  file not found"); return False

    with open(path, encoding="utf-8") as f:
        src = f.read()
    lines = src.split("\n")

    has_import = IMPORT_LINE in src
    has_decorator = "requires_plan_feature(" in src
    print(f"  has import:    {'✅' if has_import else '❌'}")
    print(f"  has decorator: {'✅' if has_decorator else '—'}")

    if not has_decorator:
        print(f"  ℹ️  no decorators used in this file — skipping")
        return has_import

    if has_import:
        # Verify import appears BEFORE first decorator usage
        import_line_no = next(i for i, ln in enumerate(lines) if IMPORT_LINE in ln)
        deco_line_no   = next(i for i, ln in enumerate(lines) if "requires_plan_feature(" in ln)
        if import_line_no < deco_line_no:
            print(f"  ✅ import at line {import_line_no+1}, first use at line {deco_line_no+1} — correct order")
            return True
        else:
            print(f"  ⚠️  import at line {import_line_no+1} appears AFTER first use at line {deco_line_no+1}")
            print(f"  🔧 moving import above decorator usage")
            del lines[import_line_no]
            # Recompute deco line after delete
            deco_line_no = next(i for i, ln in enumerate(lines) if "requires_plan_feature(" in ln)
            lines.insert(deco_line_no, IMPORT_LINE)
            with open(path, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))
            print(f"  ✅ moved")
            return True

    # Import is missing — use AST to find correct insertion point
    print(f"  🔧 inserting import via AST")
    try:
        tree = ast.parse(src)
    except SyntaxError as e:
        print(f"  ❌ file has syntax errors: {e}")
        return False

    # Find highest line number of any top-level import
    last_import_line = 0
    for node in tree.body:  # only top-level
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            last_import_line = max(last_import_line, node.end_lineno or node.lineno)

    if last_import_line > 0:
        insert_idx = last_import_line  # 0-indexed: line after the last import
        print(f"  ℹ️  last import ends at line {last_import_line} — inserting at line {insert_idx+1}")
    elif tree.body and isinstance(tree.body[0], ast.Expr) \
            and isinstance(tree.body[0].value, ast.Constant) \
            and isinstance(tree.body[0].value.value, str):
        # Module docstring exists — insert after it
        insert_idx = tree.body[0].end_lineno or tree.body[0].lineno
        print(f"  ℹ️  module docstring ends at line {insert_idx} — inserting after it")
    else:
        insert_idx = 0
        print(f"  ℹ️  no imports and no docstring — inserting at line 1")

    lines.insert(insert_idx, IMPORT_LINE)
    new_src = "\n".join(lines)

    # Verify before writing
    try:
        compile(new_src, path, "exec")
    except SyntaxError as e:
        print(f"  ❌ insertion would break syntax: {e}")
        print(f"  ℹ️  showing first 15 lines for manual inspection:")
        for i, ln in enumerate(lines[:15], 1):
            print(f"    {i:2d}: {ln}")
        return False

    with open(path, "w", encoding="utf-8") as f:
        f.write(new_src)
    print(f"  ✅ import inserted")

    try:
        py_compile.compile(path, doraise=True)
        print(f"  ✅ {path} compiles cleanly")
    except py_compile.PyCompileError as e:
        print(f"  ❌ compilation failed: {e}")
        return False

    return True


print("=" * 62)
print("DIAGNOSTIC + REPAIR")
print("=" * 62)

all_ok = True
for path in TARGETS:
    try:
        ok = diagnose(path)
        if not ok:
            all_ok = False
    except Exception as e:
        print(f"\n❌ Exception on {path}: {type(e).__name__}: {e}")
        all_ok = False

print("\n" + "=" * 62)
print("FINAL IMPORT TEST")
print("=" * 62)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "pos_backend.settings")
import django
try:
    django.setup()
    print("✅ django.setup() succeeded — all imports resolve")
except Exception as e:
    print(f"❌ Django startup failed: {type(e).__name__}: {e}")
    all_ok = False

print("\n" + ("🎉 All imports fixed — retry your test"
              if all_ok else "❌ Some files need manual attention"))
sys.exit(0 if all_ok else 1)