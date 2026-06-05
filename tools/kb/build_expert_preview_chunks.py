from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Callable, Dict, Iterable, List

ROOT = Path(__file__).resolve().parents[2]
BACKEND_SRC = ROOT / "apps" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))

from marathon_qa_assistant.services.kb.source_registry import normalize_source_record  # noqa: E402
from marathon_qa_assistant.services.vector_store import (  # noqa: E402
    DOMAIN_PACK_TO_DOMAIN,
    _merge_domain_terms,
)

GENERATED_SECTIONS = {"expert_source_registry", "pdf_paragraph_candidate", "document_paragraph"}
REPLACEABLE_SUMMARY_SECTIONS = GENERATED_SECTIONS | {"registry_preview"}
DOCUMENT_PARAGRAPH_EXTENSIONS = {".pdf", ".txt", ".md", ".docx"}
PARAGRAPH_CHUNKING_MODES = {"paragraph", "paragraphs", "pdf_paragraph", "pdf_paragraphs"}
MAX_PARAGRAPH_CHARS = 1200
HEADING_PATTERN = re.compile(
    r"^(#{1,6}\s+|PART\s+\d+|CHAPTER\s+\d+|Chapter\s+\d+|第[一二三四五六七八九十百\d]+章|目录|序言|引言|终章|致谢|参考文献)"
)
LIST_ITEM_PATTERN = re.compile(r"^([-*+•]|\d+[.)])\s+")


def _load_jsonl(path: Path) -> List[Dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, rows: Iterable[Dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "".join(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )


def _domain_terms_for_pack(domain_pack: str) -> List[str]:
    domain = DOMAIN_PACK_TO_DOMAIN.get(str(domain_pack or "").strip())
    return [domain] if domain else []


def _with_domain_terms(
    chunk: Dict[str, Any],
    records_by_source_id: Dict[str, Dict[str, Any]] | None = None,
) -> Dict[str, Any]:
    source_id = str(chunk.get("source_registry_id") or "")
    record = (records_by_source_id or {}).get(source_id) or {}
    pack = str(chunk.get("domain_pack") or record.get("domain_pack") or "")
    domain_terms = _merge_domain_terms(_domain_terms_for_pack(pack), chunk.get("domain_terms") or [])
    if not domain_terms:
        return chunk
    updated = dict(chunk)
    updated["domain_terms"] = domain_terms
    return updated


def _expert_chunk_text(record: Dict[str, Any]) -> str:
    metadata = dict(record.get("metadata") or {})
    parts = [
        str(record.get("title") or ""),
        f"Domain pack: {record.get('domain_pack') or ''}.",
        f"Evidence domain: {record.get('evidence_domain') or ''}.",
        f"Permission: {record.get('prescription_permission') or ''}.",
        str(metadata.get("summary") or metadata.get("purpose") or ""),
    ]
    return " ".join(part.strip() for part in parts if part and part.strip())


def _default_pdf_page_loader(path: Path) -> List[tuple[int, str]]:
    suffix = path.suffix.lower()
    if suffix in {".txt", ".md"}:
        return [(1, path.read_text(encoding="utf-8", errors="ignore"))]
    if suffix == ".docx":
        from docx import Document

        document = Document(str(path))
        return [(1, "\n\n".join(paragraph.text for paragraph in document.paragraphs if paragraph.text.strip()))]

    from pypdf import PdfReader

    reader = PdfReader(str(path))
    return [(index, page.extract_text() or "") for index, page in enumerate(reader.pages, start=1)]


def _resolve_local_path(record: Dict[str, Any]) -> Path:
    raw_path = str(record.get("local_path") or record.get("source_path") or "").strip()
    if not raw_path:
        raw_path = str(Path("data") / "knowledge" / "external_candidates" / str(record.get("source_file") or ""))
    path = Path(raw_path)
    return path if path.is_absolute() else ROOT / path


def _join_pdf_line(current: str, line: str) -> str:
    if not current:
        return line
    if current.endswith("-"):
        return f"{current[:-1]}{line}"
    if current[-1:].isascii() and current[-1:].isalnum() and line[:1].isascii() and line[:1].isalnum():
        return f"{current} {line}"
    return f"{current}{line}"


def _split_long_paragraph(text: str, *, max_chars: int = MAX_PARAGRAPH_CHARS) -> List[str]:
    remaining = text.strip()
    chunks: List[str] = []
    while len(remaining) > max_chars:
        cut = max(remaining.rfind(mark, 0, max_chars) for mark in ("。", "！", "？", "；", ".", "!", "?", ";"))
        if cut < max_chars // 2:
            cut = max_chars
        else:
            cut += 1
        chunks.append(remaining[:cut].strip())
        remaining = remaining[cut:].strip()
    if remaining:
        chunks.append(remaining)
    return chunks


def _split_page_into_paragraphs(text: str) -> List[Dict[str, Any]]:
    paragraphs: List[Dict[str, Any]] = []
    current = ""
    current_start = 0

    def flush(end_hint: int) -> None:
        nonlocal current, current_start
        normalized = " ".join(current.split()).strip()
        if normalized:
            for part in _split_long_paragraph(normalized):
                paragraphs.append(
                    {
                        "text": part,
                        "char_start": current_start,
                        "char_end": current_start + len(part),
                    }
                )
        current = ""
        current_start = end_hint

    offset = 0
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"):
        line = raw_line.strip()
        line_start = offset
        offset += len(raw_line) + 1
        if not line:
            flush(line_start)
            continue
        if HEADING_PATTERN.match(line):
            flush(line_start)
            current = line
            current_start = line_start
            flush(offset)
            continue
        if LIST_ITEM_PATTERN.match(line):
            flush(line_start)
            current = line
            current_start = line_start
            flush(offset)
            continue
        if not current:
            current_start = line_start
        current = _join_pdf_line(current, line)
        if line.endswith(("。", "！", "？", "；", ".", "!", "?", ";")):
            flush(offset)
    flush(offset)
    return paragraphs


def _should_build_pdf_paragraph_chunks(record: Dict[str, Any]) -> bool:
    metadata = dict(record.get("metadata") or {})
    chunking_mode = str(metadata.get("runtime_chunking") or "").strip().lower()
    source_file = str(record.get("source_file") or record.get("local_path") or record.get("source_path") or "").lower()
    return chunking_mode in PARAGRAPH_CHUNKING_MODES and source_file.endswith(".pdf")


def _should_build_document_paragraph_chunks(record: Dict[str, Any]) -> bool:
    source_path = _resolve_local_path(record)
    return source_path.exists() and source_path.suffix.lower() in DOCUMENT_PARAGRAPH_EXTENSIONS


def _paragraph_section(record: Dict[str, Any], source_path: Path) -> str:
    normalized = normalize_source_record(record)
    if source_path.suffix.lower() == ".pdf" and _should_build_pdf_paragraph_chunks(record) and normalized.review_status.value == "candidate":
        return "pdf_paragraph_candidate"
    return "document_paragraph"


def _record_to_chunk(record: Dict[str, Any], index: int, *, chunk_id: str = "") -> Dict[str, Any]:
    normalized = normalize_source_record(record)
    data = {
        "chunk_id": chunk_id or f"chunkv2_{normalized.source_registry_id}_{index:04d}",
        "source_registry_id": normalized.source_registry_id,
        "source_file": normalized.source_file,
        "source_url": normalized.source_url or f"internal://{normalized.source_registry_id}",
        "local_path": normalized.local_path or normalized.source_path or f"data/knowledge/external_candidates/{normalized.source_file}",
        "page": 1,
        "section": "expert_source_registry",
        "paragraph_index": 0,
        "char_start": 0,
        "char_end": None,
        "text": _expert_chunk_text(record),
        "language": str(record.get("language") or ("zh" if _should_build_pdf_paragraph_chunks(record) else "en")),
        "evidence_domain": normalized.evidence_domain.value,
        "knowledge_layer": "document_index",
        "domain_pack": normalized.domain_pack,
        "domain_terms": _domain_terms_for_pack(normalized.domain_pack),
        "allowed_use": normalized.allowed_use.value,
        "prescription_permission": normalized.prescription_permission.value,
        "quality_tier": normalized.quality_tier,
        "exclude_from_training_generation": normalized.prescription_permission.value != "can_write_core",
        "needs_review": normalized.needs_review,
        "review_status": normalized.review_status.value,
    }
    data["char_end"] = len(data["text"])
    return data


def _record_to_pdf_paragraph_chunk(
    record: Dict[str, Any],
    index: int,
    *,
    page: int,
    paragraph_index: int,
    paragraph: Dict[str, Any],
    section: str,
) -> Dict[str, Any]:
    normalized = normalize_source_record(record)
    paragraph_text = str(paragraph.get("text") or "").strip()
    text = f"{normalized.title}. Page {page}. {paragraph_text}"
    data = {
        "chunk_id": f"chunkv2_{normalized.source_registry_id}_{index:04d}",
        "source_registry_id": normalized.source_registry_id,
        "source_file": normalized.source_file,
        "source_url": normalized.source_url or f"internal://{normalized.source_registry_id}",
        "local_path": normalized.local_path or normalized.source_path or f"data/knowledge/external_candidates/{normalized.source_file}",
        "page": page,
        "section": section,
        "paragraph_index": paragraph_index,
        "char_start": int(paragraph.get("char_start") or 0),
        "char_end": int(paragraph.get("char_end") or len(paragraph_text)),
        "text": text,
        "language": str(record.get("language") or "zh"),
        "evidence_domain": normalized.evidence_domain.value,
        "knowledge_layer": "document_index",
        "domain_pack": normalized.domain_pack,
        "domain_terms": _domain_terms_for_pack(normalized.domain_pack),
        "allowed_use": normalized.allowed_use.value,
        "prescription_permission": normalized.prescription_permission.value,
        "quality_tier": normalized.quality_tier,
        "exclude_from_training_generation": normalized.prescription_permission.value != "can_write_core",
        "needs_review": normalized.needs_review,
        "review_status": normalized.review_status.value,
    }
    return data


def _record_to_chunks(
    record: Dict[str, Any],
    *,
    metadata_chunk_id: str = "",
    page_loader: Callable[[Path], List[tuple[int, str]]] = _default_pdf_page_loader,
) -> List[Dict[str, Any]]:
    chunks = [_record_to_chunk(record, 1, chunk_id=metadata_chunk_id)]
    source_path = _resolve_local_path(record)
    if not _should_build_document_paragraph_chunks(record):
        return chunks
    paragraph_section = _paragraph_section(record, source_path)
    source_id = normalize_source_record(record).source_registry_id
    used_chunk_ids = {str(chunk.get("chunk_id") or "") for chunk in chunks}
    next_index = 2
    for page, page_text in page_loader(source_path):
        for paragraph_index, paragraph in enumerate(_split_page_into_paragraphs(page_text), start=1):
            while f"chunkv2_{source_id}_{next_index:04d}" in used_chunk_ids:
                next_index += 1
            chunks.append(
                _record_to_pdf_paragraph_chunk(
                    record,
                    next_index,
                    page=page,
                    paragraph_index=paragraph_index,
                    paragraph=paragraph,
                    section=paragraph_section,
                )
            )
            used_chunk_ids.add(str(chunks[-1].get("chunk_id") or ""))
            next_index += 1
    return chunks


def build_expert_preview_chunks(
    *,
    registry_path: Path,
    base_preview_path: Path,
    preview_out: Path,
    page_loader: Callable[[Path], List[tuple[int, str]]] = _default_pdf_page_loader,
) -> Dict[str, Any]:
    base_chunks = _load_jsonl(base_preview_path)
    registry_rows = _load_jsonl(registry_path)
    base_source_ids = {str(chunk.get("source_registry_id") or "") for chunk in base_chunks}
    records_by_source_id = {
        str(row.get("source_registry_id") or ""): row
        for row in registry_rows
        if str(row.get("source_registry_id") or "")
    }
    paragraph_source_ids = {
        str(row.get("source_registry_id") or "")
        for row in registry_rows
        if str(row.get("source_registry_id") or "") and _should_build_document_paragraph_chunks(row)
    }
    generated_chunks_by_source_id: Dict[str, List[Dict[str, Any]]] = {}
    for chunk in base_chunks:
        source_id = str(chunk.get("source_registry_id") or "")
        section = str(chunk.get("section") or "")
        if source_id in records_by_source_id and (
            section in GENERATED_SECTIONS
            or (source_id in paragraph_source_ids and section in REPLACEABLE_SUMMARY_SECTIONS)
        ):
            generated_chunks_by_source_id.setdefault(source_id, []).append(chunk)
    refreshed_source_ids = set(generated_chunks_by_source_id) | paragraph_source_ids
    refreshed_chunks: List[Dict[str, Any]] = []
    refreshed_count = sum(len(chunks) for chunks in generated_chunks_by_source_id.values())
    for chunk in base_chunks:
        source_id = str(chunk.get("source_registry_id") or "")
        section = str(chunk.get("section") or "")
        if source_id in generated_chunks_by_source_id and section in REPLACEABLE_SUMMARY_SECTIONS:
            continue
        refreshed_chunks.append(chunk)
    existing_source_ids = {str(chunk.get("source_registry_id") or "") for chunk in refreshed_chunks}
    expert_records = [
        row
        for row in registry_rows
        if str(row.get("source_registry_id") or "") in refreshed_source_ids
        or str(row.get("source_registry_id") or "") not in existing_source_ids
    ]
    expert_chunks: List[Dict[str, Any]] = []
    new_chunk_count = 0
    for record in expert_records:
        source_id = str(record.get("source_registry_id") or "")
        old_generated_chunks = generated_chunks_by_source_id.get(source_id) or []
        old_metadata_chunk_id = next(
            (
                str(chunk.get("chunk_id") or "")
                for chunk in old_generated_chunks
                if str(chunk.get("section") or "") in {"expert_source_registry", "registry_preview"}
            ),
            "",
        )
        generated = _record_to_chunks(record, metadata_chunk_id=old_metadata_chunk_id, page_loader=page_loader)
        if source_id not in base_source_ids:
            new_chunk_count += len(generated)
        expert_chunks.extend(generated)
    all_chunks = [_with_domain_terms(chunk, records_by_source_id) for chunk in [*refreshed_chunks, *expert_chunks]]
    _write_jsonl(preview_out, all_chunks)
    return {
        "base_chunk_count": len(base_chunks),
        "expert_chunk_count": new_chunk_count,
        "paragraph_source_count": len(paragraph_source_ids),
        "paragraph_chunk_count": sum(1 for chunk in expert_chunks if str(chunk.get("section") or "") in {"pdf_paragraph_candidate", "document_paragraph"}),
        "refreshed_expert_chunk_count": refreshed_count,
        "total_chunk_count": len(all_chunks),
        "preview_out": str(preview_out),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Build expert-source chunk_schema_v2 preview without replacing v2 runtime.")
    parser.add_argument("--registry", required=True)
    parser.add_argument("--base-preview", default=str(ROOT / "data" / "knowledge" / "governance" / "chunk_schema_v2_preview.jsonl"))
    parser.add_argument("--preview-out", required=True)
    args = parser.parse_args()
    report = build_expert_preview_chunks(
        registry_path=Path(args.registry),
        base_preview_path=Path(args.base_preview),
        preview_out=Path(args.preview_out),
    )
    print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
