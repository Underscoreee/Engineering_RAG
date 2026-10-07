"""Local inspection and export helpers for the complete PDF pipeline."""

from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from time import perf_counter

from engineering_rag.chunking import EngineeringChunker
from engineering_rag.ingestion.parser import Document, PdfParser
from engineering_rag.ingestion.structure import DocumentStructure, StructureParser, StructureRole
from engineering_rag.models import Chunk

_SCANNED_TEXT_PAGE_RATIO = 0.2


@dataclass(frozen=True)
class InspectionResult:
    """The complete local pipeline output and its execution timings."""

    document: Document
    structure: DocumentStructure
    chunks: list[Chunk]
    parse_time_ms: float
    structure_time_ms: float
    chunk_time_ms: float
    total_time_ms: float


def inspect_pdf(
    pdf_path: str | Path,
    *,
    standard_name: str | None = None,
    standard_code: str | None = None,
    max_tokens: int | None = None,
) -> InspectionResult:
    """Run PdfParser, StructureParser, and EngineeringChunker in sequence."""

    total_started = perf_counter()
    parse_started = perf_counter()
    document = PdfParser().parse(
        pdf_path,
        standard_name=standard_name,
        standard_code=standard_code,
    )
    parse_time_ms = _elapsed_ms(parse_started)

    structure_started = perf_counter()
    structure = StructureParser().parse(document)
    structure_time_ms = _elapsed_ms(structure_started)

    chunk_started = perf_counter()
    chunker = EngineeringChunker() if max_tokens is None else EngineeringChunker(max_tokens=max_tokens)
    chunks = chunker.chunk(structure)
    chunk_time_ms = _elapsed_ms(chunk_started)

    return InspectionResult(
        document=document,
        structure=structure,
        chunks=chunks,
        parse_time_ms=parse_time_ms,
        structure_time_ms=structure_time_ms,
        chunk_time_ms=chunk_time_ms,
        total_time_ms=_elapsed_ms(total_started),
    )


def build_summary(result: InspectionResult) -> dict[str, object]:
    """Build a JSON-serializable summary of pipeline output and timings."""

    document = result.document
    structure = result.structure
    chunks = result.chunks
    text_pages = sum(1 for page in document.pages if page.text.strip())
    empty_text_pages = document.page_count - text_pages
    role_counts = Counter(block.role.value for block in structure.blocks)
    content_type_counts = Counter(chunk.content_type for chunk in chunks)
    for content_type in ("clause", "paragraph", "note", "explanation", "table", "formula"):
        content_type_counts.setdefault(content_type, 0)
    token_counts = [chunk.token_count for chunk in chunks]
    page_starts = [chunk.page_start for chunk in chunks]
    page_ends = [chunk.page_end for chunk in chunks]
    text_ratio = text_pages / document.page_count if document.page_count else 0.0
    possible_scanned_pdf = text_pages == 0 or text_ratio < _SCANNED_TEXT_PAGE_RATIO

    return {
        "pdf_path": document.source_file,
        "document_id": document.document_id,
        "standard_name": document.standard_name,
        "standard_code": document.standard_code,
        "page_count": document.page_count,
        "text_pages": text_pages,
        "empty_text_pages": empty_text_pages,
        "text_block_count": sum(len(page.blocks) for page in document.pages),
        "structured_block_count": len(structure.blocks),
        "chapter_count": role_counts[StructureRole.CHAPTER.value],
        "section_count": role_counts[StructureRole.SECTION.value],
        "clause_count": role_counts[StructureRole.CLAUSE.value],
        "explanation_block_count": sum(
            1 for block in structure.blocks if block.is_explanation
        ),
        "chunk_count": len(chunks),
        "content_type_counts": dict(sorted(content_type_counts.items())),
        "page_start": min(page_starts) if page_starts else None,
        "page_end": max(page_ends) if page_ends else None,
        "max_chunk_tokens": max(token_counts, default=0),
        "avg_chunk_tokens": sum(token_counts) / len(token_counts) if token_counts else 0.0,
        "has_empty_pages": empty_text_pages > 0,
        "possible_scanned_pdf": possible_scanned_pdf,
        "parse_time_ms": result.parse_time_ms,
        "structure_time_ms": result.structure_time_ms,
        "chunk_time_ms": result.chunk_time_ms,
        "total_time_ms": result.total_time_ms,
    }


def write_inspection_output(result: InspectionResult, output_dir: str | Path) -> dict[str, Path]:
    """Write complete JSON and human-readable inspection artifacts."""

    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    summary = build_summary(result)
    paths = {
        "summary": destination / "summary.json",
        "document": destination / "document.json",
        "structure": destination / "structure.json",
        "chunks": destination / "chunks.json",
        "chunks_markdown": destination / "chunks.md",
        "raw_text": destination / "raw_text.txt",
    }
    _write_json(paths["summary"], summary)
    _write_json(paths["document"], result.document.model_dump(mode="json"))
    _write_json(paths["structure"], result.structure.model_dump(mode="json"))
    _write_json(paths["chunks"], [chunk.model_dump(mode="json") for chunk in result.chunks])
    paths["chunks_markdown"].write_text(render_chunks_markdown(result.chunks), encoding="utf-8")
    paths["raw_text"].write_text(render_raw_text(result.document), encoding="utf-8")
    return paths


def render_terminal_report(
    result: InspectionResult,
    *,
    max_chunks: int,
    content_chars: int,
) -> str:
    """Render a bounded terminal report without printing the full document."""

    summary = build_summary(result)
    standard = _format_standard(result.document.standard_name, result.document.standard_code)
    content_counts = summary["content_type_counts"]
    assert isinstance(content_counts, dict)
    lines = [
        "========================================",
        "Engineering RAG PDF Inspection",
        "========================================",
        "",
        f"PDF: {summary['pdf_path']}",
        f"Document ID: {summary['document_id']}",
        f"Standard: {standard}",
        f"Pages: {summary['page_count']}",
        f"Text pages: {summary['text_pages']}",
        f"Empty pages: {summary['empty_text_pages']}",
        f"Text blocks: {summary['text_block_count']}",
        f"Structured blocks: {summary['structured_block_count']}",
        f"Chunks: {summary['chunk_count']}",
        f"Possible scanned PDF: {'YES' if summary['possible_scanned_pdf'] else 'NO'}",
        "",
        "========================================",
        "Structure Summary",
        "========================================",
        f"Chapters: {summary['chapter_count']}",
        f"Sections: {summary['section_count']}",
        f"Clauses: {summary['clause_count']}",
        f"Explanations: {summary['explanation_block_count']}",
        "",
        "========================================",
        "Chunk Summary",
        "========================================",
        f"Clause: {content_counts.get('clause', 0)}",
        f"Paragraph: {content_counts.get('paragraph', 0)}",
        f"Note: {content_counts.get('note', 0)}",
        f"Explanation: {content_counts.get('explanation', 0)}",
        f"Average tokens: {summary['avg_chunk_tokens']:.1f}",
        f"Max tokens: {summary['max_chunk_tokens']}",
    ]
    if summary["possible_scanned_pdf"]:
        lines.extend(
            [
                "",
                "WARNING: PDF may be scanned or have insufficient text layer.",
                "OCR is not implemented in the current pipeline.",
            ]
        )
    lines.extend(["", "========================================", "Sample Chunks", "========================================"])
    for index, chunk in enumerate(result.chunks[:max_chunks], start=1):
        lines.extend(
            [
                "",
                f"[Chunk {index}]",
                f"chunk_id: {chunk.chunk_id}",
                f"content_type: {chunk.content_type}",
                f"chapter: {chunk.chapter or ''}",
                f"section: {chunk.section or ''}",
                f"clause: {chunk.clause_number or ''}",
                f"page: {chunk.page_start}-{chunk.page_end}",
                "context:",
                chunk.context_header or "(none)",
                "content:",
                _truncate(chunk.content, content_chars),
                "---",
            ]
        )
    return "\n".join(lines) + "\n"


def render_chunks_markdown(chunks: list[Chunk]) -> str:
    """Render all chunks for manual review without truncating their contents."""

    lines = ["# Chunk Inspection", ""]
    for index, chunk in enumerate(chunks, start=1):
        lines.extend(
            [
                f"## Chunk {index:03d}",
                "",
                "### Metadata",
                "",
                f"- chunk_id: {chunk.chunk_id}",
                f"- logical_chunk_id: {chunk.logical_chunk_id or ''}",
                f"- parent_chunk_id: {chunk.parent_chunk_id or ''}",
                f"- content_type: {chunk.content_type}",
                f"- standard_name: {chunk.standard_name or ''}",
                f"- standard_code: {chunk.standard_code or ''}",
                f"- chapter: {chunk.chapter or ''}",
                f"- section: {chunk.section or ''}",
                f"- clause_number: {chunk.clause_number or ''}",
                f"- page_start: {chunk.page_start}",
                f"- page_end: {chunk.page_end}",
                f"- token_count: {chunk.token_count}",
                f"- is_mandatory: {chunk.is_mandatory}",
                f"- is_explanation: {chunk.is_explanation}",
                "",
                "### Section Path",
                "",
                *[f"- {part}" for part in chunk.section_path],
                "",
                "### Context Header",
                "",
                "```text",
                chunk.context_header,
                "```",
                "",
                "### Content",
                "",
                "```text",
                chunk.content,
                "```",
                "",
                "### Embedding Text",
                "",
                "```text",
                chunk.embedding_text,
                "```",
                "",
                "### Source Blocks",
                "",
                *[f"- {source_id}" for source_id in chunk.source_block_ids],
                "",
            ]
        )
    return "\n".join(lines)


def render_raw_text(document: Document) -> str:
    """Render raw page text with unambiguous page delimiters."""

    return "\n".join(
        f"===== PAGE {page.page_number} =====\n\n{page.text.rstrip()}\n"
        for page in document.pages
    )


def _elapsed_ms(started: float) -> float:
    return round((perf_counter() - started) * 1000, 3)


def _write_json(path: Path, content: object) -> None:
    path.write_text(json.dumps(content, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _format_standard(name: str | None, code: str | None) -> str:
    if name and code:
        return f"{name} ({code})"
    return name or code or "(not provided)"


def _truncate(text: str, limit: int) -> str:
    return text if len(text) <= limit else f"{text[:limit]}..."
