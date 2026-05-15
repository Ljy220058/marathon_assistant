"""Validate M-EXRxBench traceable dataset artifacts.

The script uses only the Python standard library so it can run in the paper
reproduction environment before optional validator dependencies are installed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


BENCHMARK_DIR = Path(__file__).resolve().parent
SCHEMA_PATH = BENCHMARK_DIR / "traceable_dataset_schema.json"
RULE_BASIS_SOURCES_PATH = BENCHMARK_DIR / "rule_basis_sources.json"

VISIBLE_FIELDS = {
    "case_id",
    "category",
    "user_query",
    "profile",
    "available_evidence_ids",
    "available_action_ids",
    "difficulty",
}
GOLD_FIELDS = {
    "expected_behavior",
    "gold_risk_level",
    "required_rules",
    "forbidden_outputs",
    "rationale",
}
PROVENANCE_FIELDS = {
    "case_family",
    "variation_type",
    "source_seed_id",
    "annotation_notes",
    "rule_basis_ids",
    "mapping_status",
    "mapping_confidence",
    "rule_basis_links",
}
VISIBLE_FORBIDDEN_FIELDS = GOLD_FIELDS | PROVENANCE_FIELDS
REQUIRED_REGISTRY_FIELDS = {
    "rule_basis_id",
    "source_key",
    "source_type",
    "evidence_layer",
    "rule_scope",
    "mapped_rule_ids",
    "mapped_categories",
    "risk_levels",
    "decision_effect",
    "obligations",
    "prohibitions",
    "applicable_population",
    "contraindications",
    "authority_strength",
    "promotion_status",
    "limitations",
}

RISK_BASIS_RE = re.compile(r"(^|[._-])risk([._-]|$)")
EVIDENCE_BASIS_RE = re.compile(r"(^|[._-])evidence([._-]|$)")
PROTOCOL_BASIS_RE = re.compile(r"(^|[._-])protocol([._-]|$)")
REPAIR_BASIS_RE = re.compile(r"(^|[._-])repair([._-]|$)")
FILTER_BASIS_RE = re.compile(r"(^|[._-])filter([._-]|$)")
REFUSAL_BASIS_RE = re.compile(r"(^|[._-])(refusal|refuse|refused)([._-]|$)")
MEDICAL_BASIS_RE = re.compile(r"(^|[._-])(medical|redflag|red_flag|boundary)([._-]|$)")


@dataclass(frozen=True)
class DatasetSpec:
    name: str
    expected_rows: int
    visible_file: str
    gold_file: str
    full_file: str
    basis_map_file: str


DATASETS = [
    DatasetSpec(
        name="default500",
        expected_rows=500,
        visible_file="system_visible_cases.jsonl",
        gold_file="gold_labels.jsonl",
        full_file="m_exrxbench_v0.4_500_cases.jsonl",
        basis_map_file="case_to_rule_basis_map.jsonl",
    ),
    DatasetSpec(
        name="hard100",
        expected_rows=100,
        visible_file="hard_system_visible_cases.jsonl",
        gold_file="hard_gold_labels.jsonl",
        full_file="m_exrxbench_v0.4_hard_100_cases.jsonl",
        basis_map_file="hard_case_to_rule_basis_map.jsonl",
    ),
]


class ValidationErrorCollector:
    def __init__(self) -> None:
        self.errors: list[str] = []

    def add(self, message: str) -> None:
        self.errors.append(message)

    def extend(self, messages: Iterable[str]) -> None:
        self.errors.extend(messages)


def load_json_file(path: Path, errors: ValidationErrorCollector) -> Any | None:
    if not path.exists():
        errors.add(f"missing required file: {path.name}")
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        errors.add(f"invalid JSON in {path.name}: line {exc.lineno}, column {exc.colno}: {exc.msg}")
        return None


def load_jsonl(path: Path, errors: ValidationErrorCollector) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    if not path.exists():
        errors.add(f"missing required file: {path.name}")
        return rows
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                value = json.loads(stripped)
            except json.JSONDecodeError as exc:
                errors.add(f"{path.name}:{line_number}: invalid JSON: {exc.msg}")
                continue
            if not isinstance(value, dict):
                errors.add(f"{path.name}:{line_number}: row must be a JSON object")
                continue
            rows.append(value)
    return rows


def natural_key(value: str) -> list[Any]:
    return [int(part) if part.isdigit() else part for part in re.split(r"(\d+)", value)]


def require_row_count(name: str, rows: list[dict[str, Any]], expected: int, errors: ValidationErrorCollector) -> None:
    if len(rows) != expected:
        errors.add(f"{name}: expected {expected} rows, found {len(rows)}")


def case_ids(rows: list[dict[str, Any]], dataset_name: str, view_name: str, errors: ValidationErrorCollector) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for index, row in enumerate(rows, 1):
        case_id = row.get("case_id")
        if not isinstance(case_id, str) or not case_id:
            errors.add(f"{dataset_name}/{view_name}: row {index} has missing or invalid case_id")
            continue
        if case_id in seen:
            errors.add(f"{dataset_name}/{view_name}: duplicate case_id {case_id}")
        seen.add(case_id)
        ids.append(case_id)
    if ids != sorted(ids, key=natural_key):
        errors.add(f"{dataset_name}/{view_name}: case_id order is not sorted/stable")
    return ids


def check_case_id_sets(
    dataset_name: str,
    visible_ids: list[str],
    gold_ids: list[str],
    full_ids: list[str],
    basis_ids: list[str] | None,
    errors: ValidationErrorCollector,
) -> None:
    expected = set(visible_ids)
    comparisons = {
        "gold": set(gold_ids),
        "full": set(full_ids),
    }
    if basis_ids is not None:
        comparisons["basis_map"] = set(basis_ids)
    for view_name, actual in comparisons.items():
        if actual != expected:
            missing = sorted(expected - actual, key=natural_key)[:10]
            extra = sorted(actual - expected, key=natural_key)[:10]
            errors.add(
                f"{dataset_name}: case_id mismatch in {view_name}; "
                f"missing={missing or []}, extra={extra or []}"
            )


def find_forbidden_keys(value: Any, path: str = "$") -> list[str]:
    hits: list[str] = []
    if isinstance(value, dict):
        for key, nested in value.items():
            child_path = f"{path}.{key}"
            if key in VISIBLE_FORBIDDEN_FIELDS or "gold" in key.lower() or "provenance" in key.lower():
                hits.append(child_path)
            hits.extend(find_forbidden_keys(nested, child_path))
    elif isinstance(value, list):
        for index, nested in enumerate(value):
            hits.extend(find_forbidden_keys(nested, f"{path}[{index}]"))
    return hits


def check_visible_rows(dataset_name: str, rows: list[dict[str, Any]], errors: ValidationErrorCollector) -> None:
    for index, row in enumerate(rows, 1):
        missing = sorted(VISIBLE_FIELDS - set(row))
        extra = sorted(set(row) - VISIBLE_FIELDS)
        if missing:
            errors.add(f"{dataset_name}/system_visible: row {index} missing visible fields {missing}")
        if extra:
            errors.add(f"{dataset_name}/system_visible: row {index} has non-visible fields {extra}")
        forbidden_hits = find_forbidden_keys(row)
        if forbidden_hits:
            errors.add(
                f"{dataset_name}/system_visible: row {index} leaks gold/provenance fields at "
                f"{forbidden_hits[:5]}"
            )


def check_full_matches_visible_and_gold(
    dataset_name: str,
    visible_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    full_rows: list[dict[str, Any]],
    errors: ValidationErrorCollector,
) -> None:
    visible_by_id = {row["case_id"]: row for row in visible_rows if isinstance(row.get("case_id"), str)}
    gold_by_id = {row["case_id"]: row for row in gold_rows if isinstance(row.get("case_id"), str)}
    for full in full_rows:
        case_id = full.get("case_id")
        if not isinstance(case_id, str):
            continue
        visible = visible_by_id.get(case_id)
        gold = gold_by_id.get(case_id)
        if visible:
            for field in VISIBLE_FIELDS:
                if full.get(field) != visible.get(field):
                    errors.add(f"{dataset_name}: full row {case_id} differs from visible field {field}")
        if gold:
            for field in GOLD_FIELDS:
                if field == "rationale" and full.get("rationale", full.get("notes")) == gold.get(field):
                    continue
                if field in gold and full.get(field) != gold.get(field):
                    errors.add(f"{dataset_name}: full row {case_id} differs from gold field {field}")


def extract_registry_ids(value: Any) -> set[str]:
    ids: set[str] = set()
    if isinstance(value, dict):
        for key, nested in value.items():
            if isinstance(key, str) and key.startswith("basis."):
                ids.add(key)
            if key in {"id", "basis_id", "rule_basis_id"} and isinstance(nested, str):
                ids.add(nested)
            ids.update(extract_registry_ids(nested))
    elif isinstance(value, list):
        for nested in value:
            ids.update(extract_registry_ids(nested))
    return ids


def validate_registry(registry: Any, errors: ValidationErrorCollector) -> tuple[set[str] | None, dict[str, dict[str, Any]] | None]:
    if not isinstance(registry, dict):
        errors.add("rule_basis_sources.json: registry must be an object")
        return None, None
    entries = registry.get("entries")
    if not isinstance(entries, list) or not entries:
        errors.add("rule_basis_sources.json: entries must be a non-empty list")
        return None, None
    registry_by_id: dict[str, dict[str, Any]] = {}
    seen: set[str] = set()
    for index, entry in enumerate(entries, 1):
        if not isinstance(entry, dict):
            errors.add(f"rule_basis_sources.json: entry {index} must be an object")
            continue
        basis_id = entry.get("rule_basis_id")
        if not isinstance(basis_id, str) or not basis_id.startswith("basis."):
            errors.add(f"rule_basis_sources.json: entry {index} has invalid rule_basis_id {basis_id!r}")
            continue
        if basis_id in seen:
            errors.add(f"rule_basis_sources.json: duplicate rule_basis_id {basis_id}")
        seen.add(basis_id)
        missing = sorted(REQUIRED_REGISTRY_FIELDS - set(entry))
        if missing:
            errors.add(f"rule_basis_sources.json: {basis_id} missing required fields {missing}")
        for field in ("mapped_rule_ids", "mapped_categories", "risk_levels", "obligations", "prohibitions", "limitations", "contraindications"):
            if field in entry and not isinstance(entry[field], list):
                errors.add(f"rule_basis_sources.json: {basis_id}.{field} must be a list")
        source_key = entry.get("source_key")
        source_type = entry.get("source_type")
        if isinstance(source_key, str) and source_key.startswith("local_") and source_type == "reference_bib":
            errors.add(f"rule_basis_sources.json: {basis_id} local source cannot be source_type=reference_bib")
        registry_by_id[basis_id] = entry
    return seen, registry_by_id


def get_rule_basis_ids(row: dict[str, Any], dataset_name: str, errors: ValidationErrorCollector) -> list[str]:
    case_id = str(row.get("case_id", "<missing>"))
    basis_ids = row.get("rule_basis_ids")
    if not isinstance(basis_ids, list) or not basis_ids:
        errors.add(f"{dataset_name}/basis_map: {case_id} must contain a non-empty rule_basis_ids list")
        return []
    result: list[str] = []
    for item in basis_ids:
        if not isinstance(item, str) or not item:
            errors.add(f"{dataset_name}/basis_map: {case_id} has invalid rule_basis_id {item!r}")
            continue
        result.append(item)
    if len(result) != len(set(result)):
        errors.add(f"{dataset_name}/basis_map: {case_id} has duplicate rule_basis_ids")
    return result


def contains_basis(ids: list[str], pattern: re.Pattern[str]) -> bool:
    return any(pattern.search(rule_basis_id) for rule_basis_id in ids)


def registry_entry_for(rule_basis_id: str, registry_by_id: dict[str, dict[str, Any]] | None) -> dict[str, Any] | None:
    if registry_by_id is None:
        return None
    return registry_by_id.get(rule_basis_id)


def basis_text(rule_basis_id: str, registry_by_id: dict[str, dict[str, Any]] | None) -> str:
    entry = registry_entry_for(rule_basis_id, registry_by_id)
    if not entry:
        return rule_basis_id
    parts = [rule_basis_id]
    for key in ("rule_scope", "decision_effect", "mapped_rule_ids", "mapped_categories", "prohibitions"):
        value = entry.get(key)
        if isinstance(value, list):
            parts.extend(str(item) for item in value)
        elif value is not None:
            parts.append(str(value))
    return " ".join(parts)


def contains_basis_semantic(
    ids: list[str],
    registry_by_id: dict[str, dict[str, Any]] | None,
    pattern: re.Pattern[str],
) -> bool:
    return any(pattern.search(basis_text(rule_basis_id, registry_by_id)) for rule_basis_id in ids)


def check_basis_map(
    dataset_name: str,
    basis_rows: list[dict[str, Any]],
    gold_rows: list[dict[str, Any]],
    registry_ids: set[str] | None,
    registry_by_id: dict[str, dict[str, Any]] | None,
    errors: ValidationErrorCollector,
) -> None:
    gold_by_id = {row["case_id"]: row for row in gold_rows if isinstance(row.get("case_id"), str)}
    for row in basis_rows:
        case_id = row.get("case_id")
        if not isinstance(case_id, str):
            continue
        gold = gold_by_id.get(case_id)
        risk = gold.get("gold_risk_level") if gold else None
        behavior = gold.get("expected_behavior") if gold else None
        category = row.get("category")
        basis_ids = get_rule_basis_ids(row, dataset_name, errors)
        if registry_ids is not None:
            unresolved = sorted(set(basis_ids) - registry_ids)
            if unresolved:
                errors.add(f"{dataset_name}/basis_map: {case_id} has unresolved rule_basis_ids {unresolved[:10]}")
        if row.get("mapping_status") not in {"reviewed", "accepted"}:
            errors.add(f"{dataset_name}/basis_map: {case_id} mapping_status must be reviewed or accepted")
        links = row.get("rule_basis_links", [])
        if isinstance(links, list):
            link_ids = {
                link.get("rule_basis_id")
                for link in links
                if isinstance(link, dict) and isinstance(link.get("rule_basis_id"), str)
            }
            missing_from_row = sorted(link_ids - set(basis_ids))
            if missing_from_row:
                errors.add(
                    f"{dataset_name}/basis_map: {case_id} link ids missing from rule_basis_ids "
                    f"{missing_from_row}"
                )
            for link in links:
                if not isinstance(link, dict):
                    errors.add(f"{dataset_name}/basis_map: {case_id} has non-object rule_basis_link")
                    continue
                required_rule = link.get("required_rule", "")
                link_basis_id = link.get("rule_basis_id", "")
                entry = registry_entry_for(link_basis_id, registry_by_id)
                if isinstance(required_rule, str) and isinstance(link_basis_id, str):
                    if required_rule.lower().startswith("risk.r0") and "medical_red_flag" in link_basis_id:
                        errors.add(f"{dataset_name}/basis_map: {case_id} R0 rule linked to medical-red-flag basis")
                    if risk != "R3" and "medical_red_flag.rule.001" in link_basis_id:
                        errors.add(f"{dataset_name}/basis_map: {case_id} non-R3 rule linked to red-flag refusal basis")
                if entry and isinstance(entry.get("mapped_categories"), list):
                    mapped_categories = {str(item).replace(" ", "_") for item in entry["mapped_categories"]}
                    if category not in mapped_categories and not (
                        "EvidenceGate" in entry.get("mapped_categories", [])
                        or "trace completeness" in entry.get("mapped_categories", [])
                        or "bounded repair" in entry.get("mapped_categories", [])
                        or "HMP protocol" in entry.get("mapped_categories", [])
                    ):
                        support_type = link.get("support_type")
                        if support_type == "direct" and risk != "R3":
                            errors.add(
                                f"{dataset_name}/basis_map: {case_id} direct link {required_rule}->{link_basis_id} "
                                f"does not match category {category}"
                            )
        else:
            errors.add(f"{dataset_name}/basis_map: {case_id} rule_basis_links must be a list")

        if not gold:
            continue
        if risk in {"R2", "R3"} and len(basis_ids) < 2 and not row.get("mapping_notes"):
            errors.add(f"{dataset_name}/basis_map: {case_id} {risk} case needs at least two basis ids or mapping_notes")
        if risk == "R3":
            if not contains_basis_semantic(basis_ids, registry_by_id, REFUSAL_BASIS_RE):
                errors.add(f"{dataset_name}/basis_map: {case_id} R3 case lacks refusal basis")
            if not contains_basis_semantic(basis_ids, registry_by_id, MEDICAL_BASIS_RE):
                errors.add(f"{dataset_name}/basis_map: {case_id} R3 case lacks medical-boundary basis")
        if behavior == "partial_answer":
            required_patterns = {
                "risk": RISK_BASIS_RE,
                "evidence": EVIDENCE_BASIS_RE,
                "protocol": PROTOCOL_BASIS_RE,
                "repair": REPAIR_BASIS_RE,
                "filter": FILTER_BASIS_RE,
            }
            has_any_boundary_basis = any(
                contains_basis_semantic(basis_ids, registry_by_id, pattern)
                for pattern in required_patterns.values()
            )
            if not has_any_boundary_basis:
                errors.add(
                    f"{dataset_name}/basis_map: {case_id} partial_answer lacks any "
                    "risk/evidence/protocol/repair/filter basis"
                )


def validate_dataset(
    spec: DatasetSpec,
    registry_ids: set[str] | None,
    registry_by_id: dict[str, dict[str, Any]] | None,
    errors: ValidationErrorCollector,
) -> None:
    visible_rows = load_jsonl(BENCHMARK_DIR / spec.visible_file, errors)
    gold_rows = load_jsonl(BENCHMARK_DIR / spec.gold_file, errors)
    full_rows = load_jsonl(BENCHMARK_DIR / spec.full_file, errors)
    basis_map_path = BENCHMARK_DIR / spec.basis_map_file
    basis_rows: list[dict[str, Any]] | None
    if basis_map_path.exists():
        basis_rows = load_jsonl(basis_map_path, errors)
    else:
        errors.add(f"{spec.name}: missing required basis map file: {spec.basis_map_file}")
        basis_rows = None

    require_row_count(f"{spec.name}/system_visible", visible_rows, spec.expected_rows, errors)
    require_row_count(f"{spec.name}/evaluator_gold", gold_rows, spec.expected_rows, errors)
    require_row_count(f"{spec.name}/labeled_full", full_rows, spec.expected_rows, errors)
    if basis_rows is not None:
        require_row_count(f"{spec.name}/case_rule_basis_map", basis_rows, spec.expected_rows, errors)

    visible_ids = case_ids(visible_rows, spec.name, "system_visible", errors)
    gold_ids = case_ids(gold_rows, spec.name, "evaluator_gold", errors)
    full_ids = case_ids(full_rows, spec.name, "labeled_full", errors)
    basis_ids = case_ids(basis_rows, spec.name, "case_rule_basis_map", errors) if basis_rows is not None else None
    check_case_id_sets(spec.name, visible_ids, gold_ids, full_ids, basis_ids, errors)
    check_visible_rows(spec.name, visible_rows, errors)
    check_full_matches_visible_and_gold(spec.name, visible_rows, gold_rows, full_rows, errors)
    if basis_rows is not None:
        check_basis_map(spec.name, basis_rows, gold_rows, registry_ids, registry_by_id, errors)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--benchmark-dir",
        type=Path,
        default=BENCHMARK_DIR,
        help="Benchmark directory. Defaults to the directory containing this script.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    global BENCHMARK_DIR, SCHEMA_PATH, RULE_BASIS_SOURCES_PATH
    BENCHMARK_DIR = args.benchmark_dir.resolve()
    SCHEMA_PATH = BENCHMARK_DIR / "traceable_dataset_schema.json"
    RULE_BASIS_SOURCES_PATH = BENCHMARK_DIR / "rule_basis_sources.json"

    errors = ValidationErrorCollector()
    schema = load_json_file(SCHEMA_PATH, errors)
    if isinstance(schema, dict):
        if schema.get("title") != "M-EXRxBench Traceable Dataset Schema":
            errors.add("traceable_dataset_schema.json: unexpected or missing title")
        for view_name in ("labeled_full", "system_visible", "evaluator_gold", "case_rule_basis_map"):
            if view_name not in json.dumps(schema):
                errors.add(f"traceable_dataset_schema.json: missing view definition for {view_name}")

    registry = load_json_file(RULE_BASIS_SOURCES_PATH, errors)
    registry_ids, registry_by_id = validate_registry(registry, errors) if registry is not None else (None, None)
    if registry is not None and not registry_ids:
        errors.add("rule_basis_sources.json: no basis ids could be parsed")

    for spec in DATASETS:
        validate_dataset(spec, registry_ids, registry_by_id, errors)

    if errors.errors:
        print("traceable_dataset_validation_failed", file=sys.stderr)
        for message in errors.errors:
            print(f"- {message}", file=sys.stderr)
        return 1

    print("traceable_dataset_validation_ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
