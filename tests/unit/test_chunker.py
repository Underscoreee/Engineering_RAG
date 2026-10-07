import json
import subprocess
import sys
from pathlib import Path

import pytest

from engineering_rag.chunking import EngineeringChunker, TokenCounter
from engineering_rag.ingestion.structure import (
    DocumentStructure,
    StructureRole,
    StructuredBlock,
)
from engineering_rag.models import Chunk


def block(
    text: str,
    role: StructureRole,
    *,
    page: int = 1,
    number: int = 0,
    chapter: str | None = "4 基本设计规定",
    section: str | None = "4.2 材料",
    clause_number: str | None = None,
    section_path: list[str] | None = None,
    is_explanation: bool = False,
) -> StructuredBlock:
    if section_path is None:
        section_path = [value for value in (chapter, section, clause_number) if value]
    return StructuredBlock(
        page_number=page,
        text=text,
        bbox=[10.0, 50.0, 500.0, 70.0],
        role=role,
        chapter=chapter,
        section=section,
        clause_number=clause_number,
        section_path=section_path,
        is_explanation=is_explanation,
        source_block_number=number,
    )


def document(*blocks: StructuredBlock, **metadata) -> DocumentStructure:
    return DocumentStructure(
        document_id="GB50010-2010",
        blocks=list(blocks),
        standard_name="混凝土结构设计规范",
        standard_code="GB 50010-2010",
        **metadata,
    )


def clause_block(text: str = "4.2.3 混凝土强度等级应符合规定。", **kwargs) -> StructuredBlock:
    kwargs.setdefault("clause_number", "4.2.3")
    kwargs.setdefault(
        "section_path",
        ["4 基本设计规定", "4.2 材料", kwargs["clause_number"]],
    )
    return block(
        text,
        StructureRole.CLAUSE,
        **kwargs,
    )


def test_one_clause_produces_one_clause_chunk() -> None:
    chunks = EngineeringChunker().chunk(
        document(
            block("4 基本设计规定", StructureRole.CHAPTER),
            block("4.2 材料", StructureRole.SECTION),
            clause_block(),
        )
    )

    assert len(chunks) == 1
    assert chunks[0].clause_number == "4.2.3"
    assert chunks[0].content_type == "clause"


def test_consecutive_paragraphs_join_current_clause() -> None:
    chunks = EngineeringChunker().chunk(
        document(
            clause_block(),
            block("Paragraph A", StructureRole.PARAGRAPH, number=1, clause_number="4.2.3"),
            block("Paragraph B", StructureRole.PARAGRAPH, number=2, clause_number="4.2.3"),
            block("Paragraph C", StructureRole.PARAGRAPH, number=3, clause_number="4.2.3"),
        )
    )

    assert len(chunks) == 1
    assert all(text in chunks[0].content for text in ("Paragraph A", "Paragraph B", "Paragraph C"))


def test_distinct_clauses_are_not_merged() -> None:
    second = clause_block(
        "4.2.4 结构构件应符合要求。",
        number=1,
        clause_number="4.2.4",
        section_path=["4 基本设计规定", "4.2 材料", "4.2.4"],
    )

    chunks = EngineeringChunker().chunk(document(clause_block(), second))

    assert len(chunks) == 2
    assert [chunk.clause_number for chunk in chunks] == ["4.2.3", "4.2.4"]


def test_chapter_and_section_are_context_not_chunks() -> None:
    chunks = EngineeringChunker().chunk(
        document(
            block("4 基本设计规定", StructureRole.CHAPTER),
            block("4.2 材料", StructureRole.SECTION),
            clause_block(),
        )
    )

    assert len(chunks) == 1
    assert chunks[0].content == "4.2.3 混凝土强度等级应符合规定。"


def test_clause_continues_across_pages() -> None:
    chunks = EngineeringChunker().chunk(
        document(
            clause_block(page=35),
            block("第一部分", StructureRole.PARAGRAPH, page=35, number=1, clause_number="4.2.3"),
            block("第二部分", StructureRole.PARAGRAPH, page=36, number=0, clause_number="4.2.3"),
        )
    )

    assert len(chunks) == 1
    assert (chunks[0].page_start, chunks[0].page_end) == (35, 36)
    assert chunks[0].source_block_ids == ["p35_block_0", "p35_block_1", "p36_block_0"]


def test_short_note_is_joined_to_clause() -> None:
    chunks = EngineeringChunker(short_note_max_tokens=20).chunk(
        document(
            clause_block(),
            block("注：按本规范执行。", StructureRole.NOTE, number=1, clause_number="4.2.3"),
        )
    )

    assert len(chunks) == 1
    assert "注：按本规范执行。" in chunks[0].content
    assert "p1_block_1" in chunks[0].source_block_ids


def test_long_note_is_a_child_chunk() -> None:
    chunks = EngineeringChunker(short_note_max_tokens=3).chunk(
        document(
            clause_block(),
            block("注：这是一个较长的说明注释，包含多个补充条件。", StructureRole.NOTE, number=1, clause_number="4.2.3"),
        )
    )

    assert len(chunks) == 2
    clause, note = chunks
    assert clause.content_type == "clause"
    assert note.content_type == "note"
    assert note.parent_chunk_id == clause.chunk_id


def test_explanation_is_isolated_from_normative_clause() -> None:
    chunks = EngineeringChunker().chunk(
        document(
            clause_block(),
            block("条文说明", StructureRole.EXPLANATION_HEADING, number=1),
            clause_block(
                "4.2.3 本条主要考虑材料性能。",
                number=2,
                is_explanation=True,
            ),
        )
    )

    assert len(chunks) == 2
    assert chunks[0].is_explanation is False
    assert chunks[1].is_explanation is True
    assert chunks[1].content_type == "explanation"


def test_context_header_has_standard_and_structure_metadata() -> None:
    chunk = EngineeringChunker().chunk(document(clause_block()))[0]

    assert "混凝土结构设计规范" in chunk.context_header
    assert "GB 50010-2010" in chunk.context_header
    assert "4 基本设计规定" in chunk.context_header
    assert "4.2 材料" in chunk.context_header
    assert "4.2.3" in chunk.context_header


def test_embedding_text_does_not_change_original_content() -> None:
    original = "4.2.3 混凝土强度等级应符合规定。"
    chunk = EngineeringChunker().chunk(document(clause_block(original)))[0]

    assert chunk.content == original
    assert chunk.embedding_text == f"{chunk.context_header}\n\n{original}"


def test_chunk_contains_all_source_block_ids() -> None:
    chunks = EngineeringChunker().chunk(
        document(
            clause_block(),
            block("续文", StructureRole.PARAGRAPH, number=1, clause_number="4.2.3"),
            block("注：补充", StructureRole.NOTE, number=2, clause_number="4.2.3"),
        )
    )

    assert chunks[0].source_block_ids == ["p1_block_0", "p1_block_1", "p1_block_2"]


def test_chunk_ids_are_stable_across_runs() -> None:
    structure = document(clause_block())

    first = EngineeringChunker().chunk(structure)
    second = EngineeringChunker().chunk(structure)

    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]


def test_page_range_uses_all_source_blocks() -> None:
    chunks = EngineeringChunker().chunk(
        document(
            clause_block(page=10),
            block("中间内容", StructureRole.PARAGRAPH, page=12, number=0, clause_number="4.2.3"),
        )
    )

    assert chunks[0].page_start == 10
    assert chunks[0].page_end == 12


def test_oversized_clause_splits_at_block_boundaries_and_keeps_metadata() -> None:
    structure = document(
        clause_block("4.2.3 clause title"),
        block("paragraph one words here", StructureRole.PARAGRAPH, number=1, clause_number="4.2.3"),
        block("paragraph two words here", StructureRole.PARAGRAPH, number=2, clause_number="4.2.3"),
    )
    chunks = EngineeringChunker(max_tokens=7).chunk(structure)

    assert len(chunks) > 1
    assert all(chunk.token_count <= 7 for chunk in chunks)
    assert all(chunk.clause_number == "4.2.3" for chunk in chunks)
    assert all(chunk.section_path == chunks[0].section_path for chunk in chunks)
    assert all(chunk.parent_chunk_id for chunk in chunks)
    assert {source_id for chunk in chunks for source_id in chunk.source_block_ids} == {
        "p1_block_0",
        "p1_block_1",
        "p1_block_2",
    }


def test_oversized_single_sentence_uses_token_windows() -> None:
    text = "甲乙丙丁戊己庚辛壬癸子丑寅卯辰巳午未申酉戌亥"
    chunks = EngineeringChunker(max_tokens=5).chunk(
        document(clause_block(f"4.2.3 {text}"))
    )

    assert len(chunks) > 1
    assert all(chunk.token_count <= 5 for chunk in chunks)
    assert "".join(chunk.content for chunk in chunks).replace("4.2.3 ", "") == text


def test_unknown_paragraph_without_clause_is_preserved() -> None:
    chunks = EngineeringChunker().chunk(
        document(
            block(
                "这是一段普通正文。",
                StructureRole.PARAGRAPH,
                chapter=None,
                section=None,
                section_path=[],
            )
        )
    )

    assert len(chunks) == 1
    assert chunks[0].content == "这是一段普通正文。"
    assert chunks[0].content_type == "paragraph"


def test_appendix_section_becomes_chunk_with_appendix_context() -> None:
    chunks = EngineeringChunker().chunk(
        document(
            block(
                "附录 A",
                StructureRole.APPENDIX,
                chapter="附录 A",
                section=None,
                section_path=["附录 A"],
            ),
            block(
                "A.1 材料性能",
                StructureRole.APPENDIX_SECTION,
                number=1,
                chapter="附录 A",
                section="A.1 材料性能",
                section_path=["附录 A", "A.1 材料性能"],
            ),
        )
    )

    assert len(chunks) == 1
    assert chunks[0].content == "A.1 材料性能"
    assert chunks[0].section_path == ["附录 A", "A.1 材料性能"]
    assert "附录 A" in chunks[0].context_header


def test_chunk_order_follows_document_reading_order() -> None:
    clauses = [
        clause_block(f"{number} clause", number=index, clause_number=number, section_path=[number])
        for index, number in enumerate(("4.2.3", "4.2.4", "4.2.5"))
    ]

    chunks = EngineeringChunker().chunk(document(*clauses))

    assert [chunk.clause_number for chunk in chunks] == ["4.2.3", "4.2.4", "4.2.5"]


def test_chunk_schema_defaults_preserve_task_one_construction() -> None:
    chunk = Chunk(
        chunk_id="legacy",
        document_id="doc",
        content="original",
        page_start=1,
        page_end=1,
        content_type="paragraph",
    )

    assert chunk.source_block_ids == []
    assert chunk.chapter is None
    assert chunk.embedding_text == "original"
    assert chunk.parent_chunk_id is None


def test_chunk_cli_reads_structure_json_and_writes_json(tmp_path: Path) -> None:
    input_path = tmp_path / "structure.json"
    output_path = tmp_path / "chunks.json"
    input_path.write_text(document(clause_block()).model_dump_json(), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/chunk_document.py", str(input_path), "--output", str(output_path)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    decoded = json.loads(output_path.read_text(encoding="utf-8"))
    assert len(decoded) == 1
    assert decoded[0]["clause_number"] == "4.2.3"


def test_token_counter_is_deterministic() -> None:
    counter = TokenCounter()

    assert counter.count("规范 engineering 1") == counter.count("规范 engineering 1")
