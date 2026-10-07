from pathlib import Path

import pymupdf
import pytest

from engineering_rag.chunking import EngineeringChunker
from engineering_rag.ingestion.parser import Document, PdfParser
from engineering_rag.ingestion.structure import (
    DocumentStructure,
    StructureParser,
    StructureRole,
)
from engineering_rag.models import Chunk


@pytest.fixture
def engineering_standard_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "GB50010-2010.pdf"
    pdf = pymupdf.open()
    page_text = [
        [("第一章 总则", 80), ("1.0.1 本标准适用于工程设计。", 120)],
        [("4 基本设计规定", 80), ("4.2 材料", 120)],
        [("4.2.3 混凝土强度等级应符合规定。", 80), ("这是第二段。", 112)],
        [("条文说明", 80), ("4.2.3 本条主要考虑工程安全。", 120)],
    ]
    for page_index, body_blocks in enumerate(page_text, start=1):
        page = pdf.new_page()
        page.insert_text((72, 20), "GB 50010-2010", fontname="helv")
        page.insert_text((72, 810), "第 X 页", fontname="china-s")
        for text, y in body_blocks:
            page.insert_text((72, y), text, fontname="china-s")
    pdf.save(pdf_path)
    pdf.close()
    return pdf_path


def test_pdf_to_chunk_pipeline_preserves_structure_and_metadata(
    engineering_standard_pdf: Path,
) -> None:
    parsed: Document = PdfParser().parse(
        engineering_standard_pdf,
        standard_name="混凝土结构设计规范",
        standard_code="GB 50010-2010",
    )
    structure: DocumentStructure = StructureParser().parse(parsed)
    chunks: list[Chunk] = EngineeringChunker().chunk(structure)

    assert structure.document_id == parsed.document_id
    assert structure.source_file == parsed.source_file
    assert structure.standard_name == "混凝土结构设计规范"
    assert structure.standard_code == "GB 50010-2010"
    assert len(chunks) == 3  # two normative clauses and one explanation

    clause = next(chunk for chunk in chunks if chunk.clause_number == "4.2.3" and not chunk.is_explanation)
    explanation = next(chunk for chunk in chunks if chunk.is_explanation)
    first_clause = next(chunk for chunk in chunks if chunk.clause_number == "1.0.1")

    assert clause.content_type == "clause"
    assert clause.chapter == "4 基本设计规定"
    assert clause.section == "4.2 材料"
    assert clause.section_path == ["4 基本设计规定", "4.2 材料", "4.2.3"]
    assert clause.page_start == clause.page_end == 3
    assert "这是第二段。" in clause.content
    assert clause.is_explanation is False
    assert explanation.content_type == "explanation"
    assert explanation.is_explanation is True
    assert explanation.clause_number == "4.2.3"
    assert explanation.page_start == explanation.page_end == 4
    assert first_clause.page_start == first_clause.page_end == 1

    assert "混凝土结构设计规范" in clause.context_header
    assert "GB 50010-2010" in clause.context_header
    assert "4 基本设计规定" in clause.context_header
    assert "4.2 材料" in clause.context_header
    assert "4.2.3" in clause.context_header

    all_roles = {
        f"p{block.page_number}_block_{block.source_block_number}": block.role
        for block in structure.blocks
    }
    header_footer_ids = {
        block_id
        for block_id, role in all_roles.items()
        if role in (StructureRole.HEADER, StructureRole.FOOTER)
    }
    assert len(header_footer_ids) >= 8
    chunk_source_ids = {source_id for chunk in chunks for source_id in chunk.source_block_ids}
    assert chunk_source_ids.isdisjoint(header_footer_ids)
    assert chunk_source_ids.issubset(all_roles)

    source_pages = {
        f"p{block.page_number}_block_{block.source_block_number}": block.page_number
        for block in structure.blocks
    }
    for chunk in chunks:
        pages = [source_pages[source_id] for source_id in chunk.source_block_ids]
        assert chunk.page_start == min(pages)
        assert chunk.page_end == max(pages)
        assert chunk.context_header not in chunk.content
        assert chunk.context_header in chunk.embedding_text
        assert chunk.content in chunk.embedding_text

    assert "GB 50010-2010" not in clause.content
    assert "4.2.3 混凝土强度等级应符合规定。" in clause.content
