from __future__ import annotations

import importlib.util
import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parents[1] / "tools/kb/expert_coverage_report.py"
_SPEC = importlib.util.spec_from_file_location(f"_migrated_{Path(__file__).stem}", _TARGET)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load migrated script: {_TARGET}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

# 保持旧 scripts/ 入口可 import，同时实际逻辑集中在 tools/kb/。
globals().update({name: value for name, value in vars(_MODULE).items() if not name.startswith("__")})

if __name__ == "__main__":
    runpy.run_path(str(_TARGET), run_name="__main__")
