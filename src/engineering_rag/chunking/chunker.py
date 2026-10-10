"""Clause-first chunking for engineering-standard structure models."""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field

from engineering_rag.chunking.context import ContextHeaderBuilder
from engineering_rag.chunking.token_counter import TokenCounter
from engineering_rag.ingestion.structure import (
    DocumentStructure,
    StructureRole,
    StructuredBlock,
)
from engineering_rag.models import Chunk


@dataclass
class _Draft:
    key: str
    blocks: list[StructuredBlock]
    content_type: str
    is_explanation: bool
    chapter: str | None
    section: str | None
    clause_number: str | None
    section_path: list[str]
    parent_key: str | None = None
    attached_notes: list[_Draft] = field(default_factory=list)


class ClauseGrouper:
    """Group clauses with their paragraphs and eligible notes."""

    _CONTEXT_ROLES = {
        StructureRole.CHAPTER,
        StructureRole.SECTION,
        StructureRole.APPENDIX,
    }

    def __init__(self, token_counter: TokenCounter, short_note_max_tokens: int) -> None:
        self.token_counter = token_counter
        self.short_note_max_tokens = short_note_max_tokens

    def group(self, document: DocumentStructure) -> list[_Draft]:
        drafts: list[_Draft] = []
        current: _Draft | None = None
        sequence = 0
        current_chapter: str | None = None
        current_section: str | None = None
        current_clause: str | None = None

        def new_draft(block: StructuredBlock, content_type: str, explanation: bool) -> _Draft:
            nonlocal sequence
            sequence += 1
            return _Draft(
                key=f"unit-{sequence}",
                blocks=[block],
                content_type=content_type,
                is_explanation=explanation,
                chapter=block.chapter or current_chapter,
                section=block.section or current_section,
                clause_number=block.clause_number or current_clause,
                section_path=list(block.section_path)
                or [
                    value
                    for value in (
                        block.chapter or current_chapter,
                        block.section or current_section,
                        block.clause_number or current_clause,
                    )
                    if value
                ],
            )

        def flush() -> None:
            nonlocal current
            if current is not None:
                drafts.append(current)
                drafts.extend(current.attached_notes)
                current = None

        for block in document.blocks:
            if block.role == StructureRole.EXPLANATION_HEADING:
                flush()
                current_clause = None
                continue

            if block.role in self._CONTEXT_ROLES:
                flush()
                if block.role in (StructureRole.CHAPTER, StructureRole.APPENDIX):
                    current_chapter = block.chapter or block.text.strip()
                    current_section = None
                    current_clause = None
                elif block.role == StructureRole.SECTION:
                    current_chapter = block.chapter or current_chapter
                    current_section = block.section or block.text.strip()
                    current_clause = None
                continue

            current_chapter = block.chapter or current_chapter
            current_section = block.section or current_section
            current_clause = block.clause_number or current_clause

            is_explanation = block.is_explanation
            if block.role == StructureRole.CLAUSE:
                flush()
                current = new_draft(
                    block,
                    "explanation" if is_explanation else "clause",
                    is_explanation,
                )
                continue

            if block.role == StructureRole.NOTE:
                if current is not None and current.is_explanation == is_explanation:
                    if self.token_counter.count(block.text) <= self.short_note_max_tokens:
                        current.blocks.append(block)
                    else:
                        note = new_draft(block, "note", is_explanation)
                        note.parent_key = current.key
                        current.attached_notes.append(note)
                else:
                    flush()
                    drafts.append(new_draft(block, "note", is_explanation))
                continue

            if block.role == StructureRole.APPENDIX_SECTION:
                flush()
                current_chapter = block.chapter or current_chapter
                current_section = block.section or block.text.strip()
                current_clause = None
                drafts.append(new_draft(block, "paragraph", is_explanation))
                continue

            if block.role in (StructureRole.HEADER, StructureRole.FOOTER):
                continue

            if current is not None and current.is_explanation == is_explanation:
                current.blocks.append(block)
            else:
                flush()
                content_type = "explanation" if is_explanation else "paragraph"
                drafts.append(new_draft(block, content_type, is_explanation))

        flush()
        return drafts


class OversizedChunkSplitter:
    """Split oversized content first at block, then sentence, then token bounds."""

    _SENTENCE_BOUNDARY = re.compile(r"(?<=[。！？!?；;])")
    _TOKEN = TokenCounter._TOKEN

    def __init__(self, token_counter: TokenCounter, max_tokens: int) -> None:
        self.token_counter = token_counter
        self.max_tokens = max_tokens

    def split(self, draft: _Draft) -> list[list[tuple[StructuredBlock, str]]]:
        parts: list[list[tuple[StructuredBlock, str]]] = []
        current: list[tuple[StructuredBlock, str]] = []

        for block in draft.blocks:
            text = block.text
            candidate = self._join([item_text for _, item_text in current] + [text])
            if current and self.token_counter.count(candidate) > self.max_tokens:
                parts.append(current)
                current = []

            if self.token_counter.count(text) > self.max_tokens:
                if current:
                    parts.append(current)
                    current = []
                pieces = self._split_text(text)
                parts.extend([[(block, piece)] for piece in pieces])
            else:
                current.append((block, text))

        if current:
            parts.append(current)
        return parts or [[(block, block.text.strip()) for block in draft.blocks]]

    def _split_text(self, text: str) -> list[str]:
        sentences = [part for part in self._SENTENCE_BOUNDARY.split(text) if part]
        pieces: list[str] = []
        current = ""
        for sentence in sentences:
            candidate = current + sentence
            if current and self.token_counter.count(candidate) > self.max_tokens:
                pieces.append(current)
                current = ""
            if self.token_counter.count(sentence) > self.max_tokens:
                if current:
                    pieces.append(current)
                    current = ""
                pieces.extend(self._token_windows(sentence))
            else:
                current += sentence
        if current:
            pieces.append(current)
        return pieces or [text]

    def _token_windows(self, text: str) -> list[str]:
        matches = list(self._TOKEN.finditer(text))
        if not matches:
            return [text]
        windows: list[str] = []
        start = 0
        for token_end_index in range(self.max_tokens, len(matches), self.max_tokens):
            end = matches[token_end_index - 1].end()
            windows.append(text[start:end])
            start = end
        windows.append(text[start:])
        return [window for window in windows if window]

    @staticmethod
    def _join(texts: list[str]) -> str:
        result = ""
        for text in texts:
            if (
                result
                and not result.endswith(("\n", "\r", " ", "\t"))
                and not text.startswith(("\n", "\r", " ", "\t"))
            ):
                result += "\n"
            result += text
        return result


class ChunkIdGenerator:
    """Generate stable short IDs from document, sources, type, and position."""

    @staticmethod
    def generate(
        document_id: str,
        content_type: str,
        source_block_ids: list[str],
        position: str,
    ) -> str:
        identity = "\0".join(
            [document_id, content_type, *sorted(source_block_ids), position]
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]

    @staticmethod
    def generate_logical(
        document_id: str,
        clause_number: str,
        is_explanation: bool,
        logical_position: str,
    ) -> str:
        identity = "\0".join(
            [document_id, clause_number, str(is_explanation), logical_position]
        )
        return hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24]


class EngineeringChunker:
    """Convert a DocumentStructure into citation-preserving logical chunks."""

    def __init__(
        self,
        max_tokens: int = 800,
        *,
        short_note_max_tokens: int = 80,
        token_counter: TokenCounter | None = None,
        context_header_builder: ContextHeaderBuilder | None = None,
    ) -> None:
        if max_tokens < 1:
            raise ValueError("max_tokens must be at least 1")
        if short_note_max_tokens < 0:
            raise ValueError("short_note_max_tokens cannot be negative")
        self.max_tokens = max_tokens
        self.short_note_max_tokens = short_note_max_tokens
        self.token_counter = token_counter or TokenCounter()
        self.context_header_builder = context_header_builder or ContextHeaderBuilder()

    def chunk(self, document: DocumentStructure) -> list[Chunk]:
        """Group structure blocks and return chunks in document order."""

        drafts = ClauseGrouper(
            self.token_counter,
            min(self.short_note_max_tokens, self.max_tokens),
        ).group(document)
        splitter = OversizedChunkSplitter(self.token_counter, self.max_tokens)
        chunks: list[Chunk] = []
        first_id_by_key: dict[str, str] = {}

        for draft_index, draft in enumerate(drafts):
            split_parts = splitter.split(draft)
            all_source_ids = self._source_ids(draft.blocks)
            logical_chunk_id = None
            if draft.content_type in ("clause", "explanation") and draft.clause_number:
                logical_chunk_id = ChunkIdGenerator.generate_logical(
                    document.document_id,
                    draft.clause_number,
                    draft.is_explanation,
                    all_source_ids[0] if all_source_ids else draft.key,
                )
            for part_index, part in enumerate(split_parts):
                chunk = self._make_chunk(
                    document,
                    draft,
                    part,
                    f"{draft_index}-{part_index}",
                    logical_chunk_id=logical_chunk_id,
                )
                if draft.parent_key is not None:
                    chunk.parent_chunk_id = first_id_by_key.get(draft.parent_key)
                chunks.append(chunk)
                if part_index == 0:
                    first_id_by_key[draft.key] = chunk.chunk_id

        return chunks

    def _make_chunk(
        self,
        document: DocumentStructure,
        draft: _Draft,
        parts: list[tuple[StructuredBlock, str]],
        position: str,
        logical_chunk_id: str | None,
    ) -> Chunk:
        source_blocks = [block for block, _ in parts]
        source_block_ids = self._source_ids(source_blocks)
        primary = source_blocks[0]
        content = OversizedChunkSplitter._join([text for _, text in parts])
        chapter = draft.chapter or primary.chapter
        section = draft.section or primary.section
        clause_number = draft.clause_number or primary.clause_number
        section_path = list(draft.section_path or primary.section_path)
        context_header = self.context_header_builder.build(
            standard_name=document.standard_name,
            standard_code=document.standard_code,
            chapter=chapter,
            section=section,
            clause_number=clause_number,
            section_path=section_path,
        )
        embedding_text = f"{context_header}\n\n{content}" if context_header else content
        chunk_id = ChunkIdGenerator.generate(
            document.document_id,
            draft.content_type,
            source_block_ids,
            position,
        )
        return Chunk(
            chunk_id=chunk_id,
            document_id=document.document_id,
            content=content,
            page_start=min(block.page_number for block in source_blocks),
            page_end=max(block.page_number for block in source_blocks),
            standard_name=document.standard_name,
            standard_code=document.standard_code,
            clause_number=clause_number,
            section_path=section_path,
            content_type=draft.content_type,
            is_mandatory=False,
            is_explanation=draft.is_explanation,
            chapter=chapter,
            section=section,
            source_block_ids=source_block_ids,
            context_header=context_header,
            embedding_text=embedding_text,
            token_count=self.token_counter.count(content),
            logical_chunk_id=logical_chunk_id,
        )

    @staticmethod
    def _source_ids(blocks: list[StructuredBlock]) -> list[str]:
        source_ids: list[str] = []
        for block in blocks:
            source_id = f"p{block.page_number}_block_{block.source_block_number}"
            if block.segment_index:
                source_id += f"_segment_{block.segment_index}"
            if source_id not in source_ids:
                source_ids.append(source_id)
        return source_ids
