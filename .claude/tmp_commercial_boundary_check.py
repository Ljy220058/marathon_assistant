import json
from pathlib import Path

manifest = json.loads(Path("data/knowledge/governance/expert_approved_staging_20260528_manifest.json").read_text(encoding="utf-8"))
readiness = json.loads(Path("data/knowledge/governance/commercial_readiness_report_20260528.json").read_text(encoding="utf-8"))
evidence = [
    json.loads(line)
    for line in Path("data/knowledge/governance/expert_evidence_20260528_b.jsonl").read_text(encoding="utf-8").splitlines()
    if line.strip()
]
assert manifest["commercial_staging"] is True
assert manifest["can_replace_runtime"] is False
assert manifest["runtime_vector_dir"].replace(chr(92), "/") == "data/vector_kb/expert_approved_staging_20260528"
assert readiness["can_replace_runtime"] is False
assert readiness["release_ready"] is False
assert not readiness["release_blockers"]
assert all(row["commercial_status"] == "commercial_staging_eligible" for row in evidence)
assert all(not row.get("human_reviewed") for row in evidence)
assert all(row["prescription_permission"] != "can_write_core" or row["evidence_domain"] in {"protocol", "action_library"} for row in evidence)
assert all(row["evidence_domain"] != "medical_safety" or row["allowed_use"] in {"risk_gate", "explanation"} for row in evidence)
print("deterministic commercial artifact boundary check passed")
