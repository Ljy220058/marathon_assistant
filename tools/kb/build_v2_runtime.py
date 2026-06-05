from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marathon_qa_assistant.services.kb.runtime_v2 import (  # noqa: E402
    DEFAULT_MANIFEST_PATH,
    DEFAULT_PREVIEW_PATH,
    DEFAULT_RELEASE_REPORT_PATH,
    build_v2_runtime_index,
)


def main() -> int:
    parser = argparse.ArgumentParser(description="Build data/vector_kb/v2 from chunk_schema_v2_preview.jsonl.")
    parser.add_argument("--preview-path", default=str(DEFAULT_PREVIEW_PATH))
    parser.add_argument("--output-dir", default=str(ROOT / "data" / "vector_kb" / "v2"))
    parser.add_argument("--manifest-path", default=str(DEFAULT_MANIFEST_PATH))
    parser.add_argument("--commercial-staging", action="store_true")
    parser.add_argument("--release-report-path", default=str(DEFAULT_RELEASE_REPORT_PATH))
    args = parser.parse_args()

    report = build_v2_runtime_index(
        preview_path=Path(args.preview_path),
        output_dir=Path(args.output_dir),
        manifest_path=Path(args.manifest_path),
        release_report_path=Path(args.release_report_path) if args.release_report_path else None,
        commercial_staging=args.commercial_staging,
    )
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
