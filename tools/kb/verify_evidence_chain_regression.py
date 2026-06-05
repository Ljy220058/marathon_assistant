from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Dict, List

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marathon_qa_assistant.services.kb.evidence_chain import build_evidence_chain_payload  # noqa: E402


def _build_payloads() -> Dict[str, Dict[str, Any]]:
    health_v2 = {"index_schema_version": "chunk_schema_v2", "runtime_core_prescription_enabled": True}
    health_legacy = {"index_schema_version": "legacy", "runtime_core_prescription_enabled": False}
    verified = build_evidence_chain_payload(
        query="verified protocol",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "verified-1",
                    "citation_label": "[1]",
                    "source_registry_id": "src_verified_protocol",
                    "source_file": "approved-protocol.md",
                    "source_path": "C:/private/kb/approved-protocol.md",
                    "source_url": "https://example.com/approved-protocol",
                    "page": 4,
                    "section": "week-structure",
                    "chunk_id": "approved_protocol_p0004_c0001",
                    "text": "Approved protocol text with a located source.",
                    "retrieval_mode": "vector",
                    "evidence_domain": "protocol",
                    "prescription_permission": "can_write_core",
                    "quality_tier": "approved",
                    "review_status": "approved",
                }
            ],
            "health": health_v2,
        },
        answer_text="已定位来源 [1]。",
    )
    legacy = build_evidence_chain_payload(
        query="legacy nutrition chunk",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "legacy-1",
                    "citation_label": "[1]",
                    "source_file": "Nutrition for Marathon Running.pdf",
                    "source_path": "data/vector_kb/default/nutrition.pdf",
                    "page": None,
                    "chunk_id": "2016+-+Nutrition+for+Marathon+Running_p0003_c0002",
                    "text": "Carbohydrate intake guidance for marathon runners.",
                    "retrieval_mode": "vector",
                    "evidence_domain": "sports_science_reference",
                    "prescription_permission": "explanation_only",
                }
            ],
            "health": health_legacy,
        },
        answer_text="旧知识库片段不应作为可点击引用 [1]。",
    )
    graph = build_evidence_chain_payload(
        query="graph-only recovery hint",
        evidence_bundle={
            "evidence_items": [
                {
                    "evidence_id": "graph-1",
                    "citation_label": "[1]",
                    "kind": "graph",
                    "source_file": "",
                    "page": None,
                    "section": "",
                    "chunk_id": "",
                    "text": "Recovery is related to long-run load.",
                    "retrieval_mode": "graph_local",
                    "evidence_domain": "sports_science_reference",
                    "prescription_permission": "explanation_only",
                }
            ],
            "health": health_v2,
        },
        answer_text="图谱线索不能作为可点击引用 [1]。",
    )
    return {"verified": verified, "legacy_chunk": legacy, "graph_hint": graph}


def _collect_failures(payloads: Dict[str, Dict[str, Any]]) -> List[str]:
    failures: List[str] = []
    total_leaks = sum(int(payload.get("source_path_leak_count") or 0) for payload in payloads.values())
    if total_leaks != 0:
        failures.append("source_path_leak_count_nonzero")

    verified_item = payloads["verified"]["items"][0]
    if verified_item.get("display_mode") != "verified_source":
        failures.append("verified_item_not_verified_source")
    if payloads["verified"].get("citation_gate", {}).get("status") != "passed":
        failures.append("verified_citation_gate_failed")

    legacy_item = payloads["legacy_chunk"]["items"][0]
    if legacy_item.get("display_mode") != "legacy_explanation":
        failures.append("legacy_item_wrong_display_mode")
    if not legacy_item.get("source_label") or not legacy_item.get("text_span") or legacy_item.get("page_hint") != 3:
        failures.append("legacy_item_missing_display_locator")
    legacy_gate = payloads["legacy_chunk"].get("citation_gate", {})
    if legacy_gate.get("status") != "failed" or not legacy_gate.get("violations"):
        failures.append("legacy_fake_citation_gate_not_enforced")

    graph_item = payloads["graph_hint"]["items"][0]
    if graph_item.get("display_mode") != "graph_hint":
        failures.append("graph_item_wrong_display_mode")
    if graph_item.get("source_url") or graph_item.get("page") is not None or graph_item.get("section"):
        failures.append("graph_item_has_clickable_locator")
    graph_gate = payloads["graph_hint"].get("citation_gate", {})
    if graph_gate.get("status") != "failed" or graph_gate.get("citable_labels"):
        failures.append("graph_fake_citation_gate_not_enforced")
    return failures


def main() -> int:
    payloads = _build_payloads()
    failures = _collect_failures(payloads)
    summary = {
        "ok": not failures,
        "payload_count": len(payloads),
        "source_path_leak_count": sum(int(payload.get("source_path_leak_count") or 0) for payload in payloads.values()),
        "display_modes": {name: payload["items"][0].get("display_mode") for name, payload in payloads.items()},
        "citation_gate_status": {name: payload.get("citation_gate", {}).get("status") for name, payload in payloads.items()},
        "legacy_locator_hint": payloads["legacy_chunk"]["items"][0].get("locator_hint"),
        "failures": failures,
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if not failures else 1


if __name__ == "__main__":
    raise SystemExit(main())
