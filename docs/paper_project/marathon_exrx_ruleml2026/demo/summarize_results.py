import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="Render an evaluator summary as Markdown.")
    parser.add_argument("--eval", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    data = json.loads(args.eval.read_text(encoding="utf-8"))
    lines = [
        "# Evaluation Summary",
        "",
        "| Metric | Value |",
        "|---|---:|",
    ]
    for key, value in data.items():
        if isinstance(value, float):
            rendered = f"{value:.3f}"
        else:
            rendered = str(value)
        lines.append(f"| `{key}` | {rendered} |")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
