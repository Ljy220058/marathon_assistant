"""Add deterministic sport-psychology guardrail edges to the KB graph."""
from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "apps" / "backend" / "src"))

from marathon_qa_assistant.services.knowledge_graph import GraphEngine  # noqa: E402


SOURCE_ID = "sport_psychology_subgraph_v1"


def main() -> None:
    engine = GraphEngine()
    evidence = {
        "source": "sport_psychology_curated_chunks",
        "chunk_id": SOURCE_ID,
        "text_span": "Sport psychology skills support mental preparation but do not alter training prescriptions.",
        "confidence": 0.96,
    }
    edges = [
        (
            "sport psychology skills",
            "marathon mental preparation",
            "supports",
            "concept",
            "concept",
            "Mental skills can support confidence, attention, coping, and race preparation.",
        ),
        (
            "self-talk and imagery",
            "race preparation prompts",
            "supports",
            "concept",
            "strategy",
            "Self-talk and imagery are exposed as prompts or scripts, not training plan edits.",
        ),
        (
            "sport psychology role",
            "training prescription modification",
            "constrains",
            "role",
            "constraint",
            "The psychologist role must not modify mileage, intensity, workout type, nutrition, or injury decisions.",
        ),
        (
            "persistent clinical distress",
            "professional mental-health support",
            "requires",
            "risk",
            "constraint",
            "Clinical or persistent distress is outside the assistant psychology role and should be referred out.",
        ),
    ]
    changed = 0
    for source, target, relation, source_type, target_type, description in edges:
        if engine._upsert_edge(
            source,
            target,
            relation,
            source_id=SOURCE_ID,
            source_type=source_type,
            target_type=target_type,
            evidence={**evidence, "text_span": description},
            edge_extra={
                "expert_domain": "sport_psychology",
                "graph_relation_strength": "hard_constraint" if relation in {"constrains", "requires"} else "weak_support",
            },
        ):
            changed += 1
    engine.save_graph()
    print(f"sport psychology graph edges changed: {changed}")
    print(f"nodes: {len(engine.nodes)}")
    print(f"edges: {len(engine.edges)}")


if __name__ == "__main__":
    main()
