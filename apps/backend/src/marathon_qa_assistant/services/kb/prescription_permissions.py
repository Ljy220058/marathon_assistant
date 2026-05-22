from __future__ import annotations

from marathon_qa_assistant.services.kb.models import EvidenceDomain, PrescriptionPermission


CORE_ALLOWED_DOMAINS = {
    EvidenceDomain.PROTOCOL,
    EvidenceDomain.ACTION_LIBRARY,
}


def permission_for_domain(domain: EvidenceDomain | str) -> PrescriptionPermission:
    if not isinstance(domain, EvidenceDomain):
        try:
            domain = EvidenceDomain(str(domain))
        except ValueError:
            return PrescriptionPermission.EXPLANATION_ONLY
    if domain in CORE_ALLOWED_DOMAINS:
        return PrescriptionPermission.CAN_WRITE_CORE
    if domain == EvidenceDomain.LLM_GENERAL_KNOWLEDGE:
        return PrescriptionPermission.BLOCKED_NEEDS_EVIDENCE
    return PrescriptionPermission.EXPLANATION_ONLY
