import argparse
import json
from pathlib import Path

from run_demo import DEFAULT_CASES, load_cases, run_case


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the proposed full rule-governed system.")
    parser.add_argument("--cases", type=Path, default=DEFAULT_CASES)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    cases = load_cases(args.cases)
    results = [run_case(case, system_name="full_rule_governed") for case in cases]
    payload = {
        "system": "full_rule_governed",
        "case_count": len(results),
        "results": results,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    print(text)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(text + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
