from pathlib import Path
import importlib.util
import json
import sys

root = Path(__file__).resolve().parents[2]
main_path = root / "Apps" / "CompilerAPI" / "main.py"

if str(root) not in sys.path:
    sys.path.insert(0, str(root))

spec = importlib.util.spec_from_file_location("compiler_api_main", main_path)
module = importlib.util.module_from_spec(spec)

if spec is None or spec.loader is None:
    raise RuntimeError("Could not load CompilerAPI main.py")

spec.loader.exec_module(module)

out = root / "Apps" / "CompilerAPI" / "openapi.json"
out.write_text(
    json.dumps(module.app.openapi(), indent=2, ensure_ascii=False),
    encoding="utf-8",
)

docs_out = root / "docs" / "openapi.json"
if docs_out.parent.exists():
    docs_out.write_text(out.read_text(encoding="utf-8"), encoding="utf-8")

print(f"Exported {out}")
if docs_out.exists():
    print(f"Copied to {docs_out}")
