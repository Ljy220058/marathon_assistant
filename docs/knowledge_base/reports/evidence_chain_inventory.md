# Evidence Chain Inventory

> Scope: P0 for `docs/knowledge_base/rag_evidence_chain_refactor_todo.md`. This inventory records current evidence paths, field ownership, user visibility, and known breaks before implementing the canonical evidence DTO.

## 1. Executive Summary

The current system has enough pieces to prevent some obvious evidence mistakes, but it does not yet have one canonical evidence contract.

The chain currently splits into five partially overlapping shapes:

- Retrieval evidence: `rag_sources`, `ranked_evidence`, `evidence_bundle`, `evidence_base`.
- Plan evidence: `structured_training_plan`, `monthly_training_calendar`, `daily_schedule_cards`.
- Daily card evidence: `evidence_tier`, `field_sources`, `action_match`, `kb_metadata`, `trace`.
- Runtime governance evidence: `source_registry_v2`, `source_review_summary`, `runtime_index_v2_manifest`, `legacy_runtime_quarantine_report`.
- Frontend evidence display: `collectEvidenceItems()`, `renderEvidencePreview()`, `buildDayEvidenceItems()`, `openEvidenceDrawer()`.

The main risk is not that the project lacks evidence concepts. The risk is that these concepts are parallel and can disagree. Until P1-P3 are done, the frontend must treat backend evidence as partial and must not upgrade legacy or model-general explanations into verified citations.

## 2. Current Runtime Facts

| Area | Current Fact | Product Meaning |
| --- | --- | --- |
| Runtime vector KB | `1160` chunks from `9` source files, legacy schema only | Explanation fallback only; not core prescription evidence |
| Runtime metadata | chunks only have `chunk_id/page/source_file/text` | Cannot support source registry citation or permission checks end to end |
| Source registry v2 | `750` records | Governance seed exists |
| Source readiness | `707 seed_only`, `43 candidate`, `0 approved`, `0 ready` | No source can be called approved runtime evidence |
| Runtime v2 manifest | `preview_only_not_runtime`, `can_replace_runtime=false` | v2 cannot replace default runtime |
| Quarantine | `10078-60-2017-v60-2017-28.pdf` quarantined | Must not appear in user-visible citation |
| Golden questions v2 | `110` ready questions | Eval fixture exists, but not yet a full RAG-vs-base runner |

## 3. Evidence Path Inventory

### 3.1 Retrieval Path

| Step | Code Anchor | Inputs | Outputs | Current Issue |
| --- | --- | --- | --- | --- |
| Runtime bootstrap | `apps/backend/src/marathon_qa_assistant/core/kb_bootstrap.py` | vector dir health | `index_schema_version`, `runtime_core_prescription_enabled` | Health exists but downstream display does not fully enforce it |
| Query retrieval | `nodes/common.py:get_context` | query, `KB_CHUNKS`, `RETRIEVE_FUNC` | raw hits | returns empty on failure without evidence status object |
| Hit projection | `nodes/common.py:build_rag_sources` | raw hits | `source/source_file/source_path/page/score/chunk_id/snippet/text` | drops v2 permission metadata |
| Ranked merge | `nodes/profile_and_retrieval.py:build_ranked_evidence` | vector hits + graph edges | `ranked_evidence` with citation labels | vector hits are flattened to legacy fields |
| Evidence bundle | `core/evidence_bundle.py:build_evidence_bundle` | `rag_sources`, `ranked_evidence`, plan | `evidence_items` | mixes flattened legacy items with protocol items |
| Evidence base | `core/evidence_bundle.py:evidence_base_from_bundle` | `evidence_bundle` | `evidence_base` | exposes `source_path` and lacks public/expert projection |

Required P1/P2 fix: `build_rag_sources` and `build_ranked_evidence` must preserve all v2 fields, and `evidence_base` must become a projection from canonical `evidence_chain.items`.

### 3.2 Plan Generation Path

| Step | Code Anchor | Inputs | Outputs | Current Issue |
| --- | --- | --- | --- | --- |
| Skeleton state | `apps/api_app.py:_build_skeleton_state` | query, profile | `structured_training_plan`, protocol evidence bundle | skeleton route can produce plan evidence without retrieval |
| Calendar contract | `apps/api_app.py:_calendar_contract_from_plan` | structured plan | daily cards, load summary, review | evidence review is derived after cards exist |
| Response assembly | `apps/api_app.py:_query_response_from_state` | graph result state | `QueryResponse` | no canonical `answer_source_mode` in schema yet |
| Workflow trace | `core/state_models.py:build_workflow_trace` | evidence bundle, plan, feedback | `evidence_state` | evidence state only counts items and missing conditions |

Required P4/P5 fix: all plan responses need `answer_source_mode` plus runtime evidence boundary so the UI can distinguish structured rules, model knowledge, needs evidence, and medical referral.

### 3.3 Daily Card Path

| Step | Code Anchor | Inputs | Outputs | Current Issue |
| --- | --- | --- | --- | --- |
| Action template | `services/workout_template_retriever.py:WorkoutTemplateCard.to_dict` | matched action card | `kb_metadata` | metadata generated from source labels, not source registry review state |
| Daily generation | `services/daily_schedule_generator.py:DailyScheduleDay` | plan day + card + fallback | user-visible day card | rich evidence fields exist |
| Field source build | `daily_schedule_generator.py:_build_field_sources` | evidence tier + card + protocol check | `field_sources` | core fields are guarded, but not mapped to canonical evidence item |
| Action match | `daily_schedule_generator.py:_build_action_match` | workout type + card | `action_match` | source/page/action id not normalized to evidence DTO |
| Needs evidence | `daily_schedule_generator.py:_needs_evidence_card` and related branches | missing action/protocol | `needs_evidence` day | works, but frontend can still compose a model-knowledge evidence item |

Required P6 fix: every `field_sources.main_set` must point to a canonical evidence item or an explicit `needs_evidence` item. The frontend should stop using hard-coded action-library source defaults.

### 3.4 GraphRAG Path

| Step | Code Anchor | Inputs | Outputs | Current Issue |
| --- | --- | --- | --- | --- |
| Entity extraction | `profile_and_retrieval.py:entity_extraction_node` | query | entities | simple entity extraction, useful for recall |
| Graph search | `nodes/common.py:get_graph_context` | entities | graph context + Mermaid | graph text can influence prompt/explanation |
| Graph evidence binding | `services/kb/graph_evidence.py:evidence_from_graph_edge` | graph edge evidence | `EvidenceBinding` | permission derives from domain, but source anchor may be weak |
| Legacy conversion | `graph_binding_to_legacy_evidence` | binding | graph-like legacy evidence | loses display boundary unless canonical DTO is added |
| Ranking fusion | `build_ranked_evidence` | vector + graph | citation-labeled evidence | graph-only item can be ranked alongside vector source |

Required P7 fix: graph-only evidence without `source_url/page/section/chunk_id` must be `graph_hint`, never `verified_source`.

### 3.5 Frontend Evidence Display Path

| Step | Code Anchor | Inputs | Outputs | Current Issue |
| --- | --- | --- | --- | --- |
| Evidence collection | `apps/web/src/scripts/app.js:collectEvidenceItems` | response | frontend evidence items | reconstructs backend evidence into another shape |
| Preview list | `renderEvidencePreview` | frontend items | evidence cards | can display frontend-composed items |
| Day evidence | `buildDayEvidenceItems` | selected day | day-specific evidence items | may synthesize action library or model knowledge items |
| Drawer rendering | `renderEvidenceDrawerItem` | frontend item | drawer DOM | display boundary depends on frontend item shape |
| Drawer open | `openEvidenceDrawer` | context | modal content | no backend canonical item requirement yet |

Required P8 fix: frontend should consume canonical backend `evidence_chain.items` first and only use compatibility fallback for old responses.

## 4. Field Ownership Matrix

| Field | Current Producer | Current Consumer | Visibility | Prescription Permission Impact | Required Owner After Refactor |
| --- | --- | --- | --- | --- | --- |
| `rag_sources` | `build_rag_sources` | prompt/report builders, workout template retriever | expert/debug only | none directly | backend retrieval layer |
| `ranked_evidence` | `build_ranked_evidence` | evidence bundle, logs | expert/debug only | none directly | backend retrieval layer |
| `evidence_bundle.evidence_items` | `build_evidence_bundle` | structured report, workflow trace, auditor | compatibility public/expert mixed | partial | canonical evidence service |
| `evidence_base` | `evidence_base_from_bundle` | structured report, frontend | public/expert mixed | none directly | projection from canonical DTO |
| `citation_label` | `build_ranked_evidence` / `_renumber` | final report, evidence drawer | public only if verified | citation faithfulness | canonical evidence service |
| `source_file` | retrieval/doc metadata | backend + frontend | public label only after projection | none alone | canonical evidence service |
| `source_path` | vector metadata/inference | backend + frontend | expert only; should not public leak | none | backend expert projection |
| `source_url` | v2 metadata | currently preserved in some bindings | public only if verified | required for verified source | source registry/runtime hit |
| `page` | chunk metadata | backend + frontend | public if verified | citation position | source registry/runtime hit |
| `section` | v2 metadata | currently partial | public if verified | citation position | source registry/runtime hit |
| `source_registry_id` | v2 registry or fallback hash | backend tests/expert | expert only | source review lookup | source registry |
| `evidence_domain` | v2 metadata/binding | backend tests/frontend labels | public label, expert raw | domain permission | source registry |
| `knowledge_layer` | v2 metadata/binding | backend tests | expert only | contextual | source registry |
| `allowed_use` | v2 metadata | backend future gate | expert only | evidence boundary | source registry |
| `prescription_permission` | v2 metadata/binding/action card | backend + frontend | public status, expert raw | core field gate | source registry |
| `review_status` | source review queue | governance docs | expert/status only | release gate | source review workflow |
| `evidence_tier` | daily schedule generator | frontend day cards | public | broad status | daily schedule generator |
| `field_sources` | daily schedule generator | frontend audit/review | expert by default; summarized public | core field gate | daily schedule generator + canonical evidence service |
| `kb_metadata` | action template/daily generator | review/tests/frontend | expert by default | core permission support | action library + canonical evidence service |
| `action_match` | daily schedule generator | frontend day evidence | expert/default hidden except status | main-set evidence | action library |
| `answer_source_mode` | not canonical yet | future frontend | public status | route-level boundary | API response builder |

## 5. Visibility Rules

### Public Runner Layer

Allowed:

- `display_mode`
- `source_label`
- `source_url` only when `display_mode=verified_source`
- `page` or `section` only when `display_mode=verified_source`
- `user_facing_summary`
- high-level source type label, such as `动作库`, `HMP 基石协议`, `模型常识说明`, `待补证据`

Not allowed:

- `source_path`
- `local_path`
- absolute Windows paths
- raw `source_registry_id`
- retrieval score
- graph node ids
- internal `hm_*` ids
- raw `workflow_trace`
- raw `field_sources`
- raw `action_match`

### Expert Layer

Allowed:

- `source_registry_id`
- `retrieval_mode`
- `score`
- `prescription_permission`
- `allowed_use`
- `quality_tier`
- `review_status`
- `source_path` only if sanitized and useful for local debugging
- graph relation trace
- field-source trace

Expert layer still must not expose secrets, API keys, Authorization headers, or user private notes that were not explicitly saved as profile facts.

## 6. Evidence Display Modes

| Display Mode | Meaning | Citation Badge | Can Write Core Prescription | Current Source |
| --- | --- | --- | --- | --- |
| `verified_source` | real source with source URL and page/section | yes | only if domain/permission allow | future canonical DTO |
| `model_general_knowledge` | model answer without local evidence | no | no | missing-info fallback |
| `needs_evidence` | core evidence missing | no | no | daily schedule / evidence gate |
| `graph_hint` | graph relation without source anchor | no | no | GraphRAG |
| `legacy_explanation` | legacy vector chunk without v2 metadata | no in public layer | no | current runtime KB |
| `rejected_source` | quarantined/blocked source | no | no | source review/quarantine |

## 7. Known Chain Breaks To Fix Next

1. `build_rag_sources()` drops v2 metadata.
2. `build_ranked_evidence()` drops v2 metadata from vector hits.
3. `evidence_base_from_bundle()` returns `source_path` without role projection.
4. `QueryResponse` lacks canonical `answer_source_mode`.
5. `evidence_bundle` renumbers mixed evidence without source-display validation.
6. Graph-only evidence can be ranked beside source-backed vector evidence.
7. Frontend synthesizes day evidence items instead of only consuming backend evidence items.
8. Frontend can display model knowledge as an evidence drawer item without backend-signed display mode.
9. Runtime health reports legacy status, but `/query` does not force every hit into `legacy_explanation`.
10. Source review status is not yet enforced in runtime answer display.
11. Training plan review catches some core source violations but does not validate every user-visible citation.
12. There is no single commercial evidence-chain gate report yet.

## 8. P1 Input Requirements

P1 should define canonical DTOs that satisfy this inventory:

```json
{
  "evidence_chain": {
    "answer_source_mode": "verified_rag | model_general_knowledge | needs_evidence | medical_referral | structured_plan_rule",
    "runtime_index_schema_version": "legacy | mixed | chunk_schema_v2 | empty",
    "runtime_core_prescription_enabled": false,
    "items": [
      {
        "evidence_id": "stable-id",
        "display_mode": "verified_source | model_general_knowledge | needs_evidence | graph_hint | legacy_explanation | rejected_source",
        "source_label": "user-facing label",
        "source_registry_id": "expert-only",
        "source_url": "",
        "page": null,
        "section": "",
        "chunk_id": "",
        "text_span": "",
        "evidence_domain": "protocol | action_library | sports_science_reference | llm_general_knowledge",
        "knowledge_layer": "document_index | domain_graph | prescription_library",
        "allowed_use": "core_prescription | explanation | risk_gate | evaluation_only",
        "prescription_permission": "can_write_core | explanation_only | blocked_needs_evidence",
        "retrieval_mode": "vector | graph_local | action_library | protocol_rule | none",
        "quality_tier": "approved | candidate | seed_only | legacy",
        "review_status": "approved | reviewed | candidate | seed_only | blocked",
        "field_binding": {
          "day_key": "",
          "field": "main_set"
        },
        "user_facing_summary": "",
        "expert_metadata": {}
      }
    ],
    "fake_citation_violations": [],
    "core_permission_violations": [],
    "source_path_leak_count": 0
  }
}
```

## 9. Acceptance Checklist

- [x] Backend retrieval path inventoried.
- [x] Plan generation path inventoried.
- [x] Daily card path inventoried.
- [x] GraphRAG path inventoried.
- [x] Frontend EvidenceDrawer path inventoried.
- [x] Field ownership table created.
- [x] Display mode enum proposed.
- [x] P1 DTO input requirements defined.

## 10. Verification

Target verification for this P0 inventory:

```powershell
$env:PYTHONUTF8='1'
$env:PYTHONPATH='apps/backend/src'
python -m pytest tests/test_kb_evidence_binding.py tests/test_openapi_contract.py -q
git diff --check -- docs/knowledge_base/reports/evidence_chain_inventory.md docs/knowledge_base/rag_evidence_chain_refactor_todo.md
```

