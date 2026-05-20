from __future__ import annotations

import importlib.util
import runpy
from pathlib import Path

_TARGET = Path(__file__).resolve().parents[1] / "tools/research/stai/run_stai_s1_vanilla_rag.py"
_SPEC = importlib.util.spec_from_file_location(f"_migrated_{Path(__file__).stem}", _TARGET)
if _SPEC is None or _SPEC.loader is None:
    raise ImportError(f"Cannot load migrated script: {_TARGET}")
_MODULE = importlib.util.module_from_spec(_SPEC)
_SPEC.loader.exec_module(_MODULE)

globals().update({name: value for name, value in vars(_MODULE).items() if not name.startswith("__")})

if __name__ == "__main__":
    runpy.run_path(str(_TARGET), run_name="__main__")