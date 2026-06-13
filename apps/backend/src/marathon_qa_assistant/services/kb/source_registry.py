from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

from marathon_qa_assistant.services.kb.models import (
    AllowedUse,
    EvidenceDomain,
    KnowledgeLayer,
    PrescriptionPermission,
    SourceQuality,
    SourceRecord,
    SourceReviewStatus,
)


DOMAIN_PACK_TO_EVIDENCE_DOMAIN = {
    "training_protocols": EvidenceDomain.PROTOCOL,
    "action_library": EvidenceDomain.ACTION_LIBRARY,
    "environment_race_context": EvidenceDomain.ENVIRONMENT_RACE_CONTEXT,
    "medical_risk": EvidenceDomain.MEDICAL_SAFETY,
    "nutrition_race_fueling": EvidenceDomain.NUTRITION_RACE_FUELING,
    "rehab_return_to_run": EvidenceDomain.REHAB_STRENGTH_MOBILITY,
    "competitor_product_reference": EvidenceDomain.COMPETITOR_PRODUCT_REFERENCE,
    "user_profile_case": EvidenceDomain.USER_PROFILE_CASE,
}


def build_source_registry_id(source: str) -> str:
    normalized = " ".join(str(source or "").replace("\\", "/").split()).strip().lower()
    if not normalized:
        raise ValueError("source is required")
    digest = hashlib.sha1(normalized.encode("utf-8")).hexdigest()[:12]
    return f"src_{digest}"


def _quality_from_dict(value: Any) -> Optional[SourceQuality]:
    if not isinstance(value, dict):
        return None
    return SourceQuality(
        tier=str(value.get("tier") or "unknown"),
        freshness_status=str(value.get("freshness_status") or "unknown"),
        applicability=[str(item) for item in value.get("applicability") or []],
        contraindications=[str(item) for item in value.get("contraindications") or []],
        notes=str(value.get("notes") or ""),
    )


def _enum_value(enum_cls: Any, raw: Any, default: Any) -> Any:
    try:
        return enum_cls(str(raw or default.value))
    except ValueError:
        return default


def _stable_content_hash(*parts: str) -> str:
    normalized = "\n".join(str(part or "").replace("\\", "/").strip() for part in parts if str(part or "").strip())
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()[:24]


def _contains_mojibake(value: Any) -> bool:
    text = str(value or "")
    return "????" in text or "\ufffd" in text


def _infer_evidence_domain(payload: Dict[str, Any]) -> EvidenceDomain:
    raw_domain = str(payload.get("evidence_domain") or "").strip()
    if raw_domain:
        try:
            return EvidenceDomain(raw_domain)
        except ValueError:
            pass
    domain_pack = str(payload.get("domain_pack") or payload.get("group") or "").strip()
    if domain_pack in DOMAIN_PACK_TO_EVIDENCE_DOMAIN:
        return DOMAIN_PACK_TO_EVIDENCE_DOMAIN[domain_pack]
    source_file = str(payload.get("source_file") or payload.get("source_path") or "").lower()
    if any(term in source_file for term in ("protocol", "plan", "guide")):
        return EvidenceDomain.PROTOCOL
    if any(term in source_file for term in ("nutrition", "fuel", "hydration", "electrolyte")):
        return EvidenceDomain.NUTRITION_RACE_FUELING
    if any(term in source_file for term in ("injury", "rehab", "return_to_run", "pain")):
        return EvidenceDomain.REHAB_STRENGTH_MOBILITY
    if any(term in source_file for term in ("heat", "weather", "altitude", "environment")):
        return EvidenceDomain.ENVIRONMENT_RACE_CONTEXT
    return EvidenceDomain.SPORTS_SCIENCE_REFERENCE


def _review_status_from_payload(payload: Dict[str, Any], *, needs_review: bool) -> SourceReviewStatus:
    raw = str(payload.get("review_status") or "").strip()
    source_type = str(payload.get("source_type") or "").strip()
    if source_type == "internal_structured_rule_seed":
        return SourceReviewStatus.SEED_ONLY
    if raw:
        try:
            return SourceReviewStatus(raw)
        except ValueError:
            return SourceReviewStatus.CANDIDATE
    if needs_review:
        return SourceReviewStatus.CANDIDATE
    return SourceReviewStatus.APPROVED


def normalize_source_record(payload: Dict[str, Any]) -> SourceRecord:
    source_file = str(payload.get("source_file") or "").strip()
    source_path = str(payload.get("source_path") or payload.get("local_path") or "").strip()
    source_key = source_path or source_file
    if not source_key:
        raise ValueError("source_file or source_path is required")

    evidence_domain = _infer_evidence_domain(payload)
    knowledge_layer = _enum_value(
        KnowledgeLayer,
        payload.get("knowledge_layer"),
        KnowledgeLayer.SOURCE_REGISTRY,
    )
    allowed_use = _enum_value(AllowedUse, payload.get("allowed_use"), AllowedUse.EXPLANATION)
    prescription_permission = _enum_value(
        PrescriptionPermission,
        payload.get("prescription_permission"),
        PrescriptionPermission.EXPLANATION_ONLY,
    )
    source_registry_id = str(payload.get("source_registry_id") or build_source_registry_id(source_key))
    title = str(payload.get("title") or source_file or source_path)
    quality = _quality_from_dict(payload.get("quality"))
    metadata = dict(payload.get("metadata") or {})
    needs_review = bool(payload.get("needs_review", True))
    if _contains_mojibake(payload.get("purpose")) or _contains_mojibake(metadata.get("purpose")):
        needs_review = True
    review_status = _review_status_from_payload(payload, needs_review=needs_review)
    if review_status in {SourceReviewStatus.CANDIDATE, SourceReviewStatus.EXTRACTED, SourceReviewStatus.REVIEWED, SourceReviewStatus.SEED_ONLY}:
        needs_review = True

    return SourceRecord(
        source_registry_id=source_registry_id,
        title=title,
        evidence_domain=evidence_domain,
        knowledge_layer=knowledge_layer,
        source_type=str(payload.get("source_type") or ""),
        authors_or_owner=str(payload.get("authors_or_owner") or payload.get("authors") or payload.get("owner") or ""),
        year=str(payload.get("year") or ""),
        source_url=str(payload.get("source_url") or payload.get("url") or ""),
        local_path=str(payload.get("local_path") or source_path),
        license_status=str(payload.get("license_status") or payload.get("license_note") or "unknown"),
        download_status=str(payload.get("download_status") or ""),
        content_hash=str(payload.get("content_hash") or _stable_content_hash(source_key, title, str(payload.get("url") or ""))),
        domain_pack=str(payload.get("domain_pack") or payload.get("group") or ""),
        allowed_use=allowed_use,
        prescription_permission=prescription_permission,
        quality_tier=str(payload.get("quality_tier") or (quality.tier if quality else "unknown")),
        freshness_status=str(payload.get("freshness_status") or (quality.freshness_status if quality else "unknown")),
        applicable_runner_segments=[str(item) for item in payload.get("applicable_runner_segments") or []],
        contraindications=[str(item) for item in payload.get("contraindications") or []],
        needs_review=needs_review,
        review_status=review_status,
        source_file=source_file,
        source_path=source_path,
        published_at=str(payload.get("published_at") or ""),
        updated_at=str(payload.get("updated_at") or ""),
        quality=quality,
        metadata=metadata,
    )


def source_record_to_dict(record: SourceRecord) -> Dict[str, Any]:
    return {
        "source_registry_id": record.source_registry_id,
        "source_type": record.source_type,
        "title": record.title,
        "authors_or_owner": record.authors_or_owner,
        "year": record.year,
        "source_url": record.source_url,
        "local_path": record.local_path,
        "license_status": record.license_status,
        "download_status": record.download_status,
        "content_hash": record.content_hash,
        "evidence_domain": record.evidence_domain.value,
        "knowledge_layer": record.knowledge_layer.value,
        "domain_pack": record.domain_pack,
        "allowed_use": record.allowed_use.value,
        "prescription_permission": record.prescription_permission.value,
        "quality_tier": record.quality_tier,
        "freshness_status": record.freshness_status,
        "applicable_runner_segments": record.applicable_runner_segments,
        "contraindications": record.contraindications,
        "needs_review": record.needs_review,
        "review_status": record.review_status.value,
        "source_file": record.source_file,
        "source_path": record.source_path,
        "metadata": record.metadata,
    }


def validate_source_registry_v2(record: SourceRecord) -> List[str]:
    errors: List[str] = []
    required = {
        "source_registry_id": record.source_registry_id,
        "title": record.title,
        "evidence_domain": record.evidence_domain.value,
        "knowledge_layer": record.knowledge_layer.value,
        "allowed_use": record.allowed_use.value,
        "prescription_permission": record.prescription_permission.value,
        "content_hash": record.content_hash,
    }
    for field_name, value in required.items():
        if not str(value or "").strip():
            errors.append(f"missing_{field_name}")
    if record.prescription_permission == PrescriptionPermission.CAN_WRITE_CORE and record.evidence_domain not in {
        EvidenceDomain.PROTOCOL,
        EvidenceDomain.ACTION_LIBRARY,
    }:
        errors.append("core_permission_domain_violation")
    if not (record.source_url or record.local_path or record.source_path or record.source_file):
        errors.append("missing_source_location")
    if _contains_mojibake(record.metadata.get("purpose")) and not record.needs_review:
        errors.append("mojibake_purpose_marked_ready")
    return errors


def source_record_is_ready(record: SourceRecord) -> bool:
    return (
        record.review_status == SourceReviewStatus.APPROVED
        and not record.needs_review
        and not validate_source_registry_v2(record)
    )


def paper_card_to_registry_record(card: Dict[str, Any]) -> SourceRecord:
    download = card.get("download") if isinstance(card.get("download"), dict) else {}
    local_pdf = str(card.get("local_pdf") or download.get("path") or "")
    source_file = Path(local_pdf).name if local_pdf else f"{card.get('id', 'paper_card')}.metadata"
    domain_pack = str(card.get("group") or "")
    metadata = {
        "paper_card_id": str(card.get("id") or ""),
        "purpose": str(card.get("purpose") or ""),
        "tags": list(card.get("tags") or []),
        "doi": str(card.get("doi") or ""),
        "pdf_url": str(card.get("pdf_url") or ""),
    }
    return normalize_source_record(
        {
            "source_registry_id": f"src_{card.get('id')}" if card.get("id") else "",
            "source_type": card.get("source_type") or "academic_literature",
            "title": card.get("title"),
            "authors_or_owner": card.get("authors"),
            "year": card.get("year"),
            "source_url": card.get("url"),
            "source_file": source_file,
            "source_path": local_pdf,
            "local_path": local_pdf,
            "license_status": card.get("license_note") or "verify_before_redistribution",
            "download_status": download.get("status") or "metadata_only",
            "evidence_domain": EvidenceDomain.SPORTS_SCIENCE_REFERENCE.value,
            "knowledge_layer": KnowledgeLayer.SOURCE_REGISTRY.value,
            "domain_pack": domain_pack,
            "allowed_use": AllowedUse.EXPLANATION.value,
            "prescription_permission": PrescriptionPermission.EXPLANATION_ONLY.value,
            "quality_tier": card.get("source_type") or "academic_literature",
            "freshness_status": "current" if int(card.get("year") or 0) >= 2018 else "aging",
            "needs_review": _contains_mojibake(card.get("purpose")) or not local_pdf,
            "metadata": metadata,
        }
    )


def load_paper_cards(path: str | Path) -> List[Dict[str, Any]]:
    cards: List[Dict[str, Any]] = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            cards.append(json.loads(line))
    return cards


def build_registry_v2_from_paper_cards(cards: Iterable[Dict[str, Any]]) -> List[SourceRecord]:
    return [paper_card_to_registry_record(card) for card in cards]
