import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

from engineering_rag.ingestion.parser import Document, Page, PdfParser, TextBlock
from engineering_rag.ingestion.structure import (
    DocumentStructure,
    StructureParser,
    StructureRole,
)


def make_document(*texts: str) -> Document:
    return Document(
        document_id="test-standard",
        source_file="test-standard.pdf",
        page_count=1,
        pages=[
            Page(
                page_number=1,
                text="\n".join(texts),
                blocks=[
                    TextBlock(
                        text=text,
                        bbox=[10.0, 50.0 + index * 20, 500.0, 65.0 + index * 20],
                        block_number=index,
                        block_type=0,
                    )
                    for index, text in enumerate(texts)
                ],
            )
        ],
    )


@pytest.fixture
def structured_five_page_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "structure-sample.pdf"
    pdf = pymupdf.open()
    contents = [
        [("Engineering Standard", 20, "hebo"), ("第一章 总则", 14, "china-s"), ("1.0.1 本标准适用于……", 12, "china-s")],
        [("4 基本设计规定", 14, "china-s"), ("4.2 材料", 12, "china-s")],
        [("4.2.3 混凝土强度等级……", 12, "china-s"), ("注：……", 10, "china-s")],
        [("条文说明", 16, "hebo"), ("4.2.3 本条说明……", 12, "china-s")],
        [("附录 A", 14, "hebo"), ("A.1 ……", 12, "china-s")],
    ]
    for page_index, page_items in enumerate(contents):
        page = pdf.new_page()
        for line_index, (text, font_size, font_name) in enumerate(page_items):
            page.insert_text(
                (72, 60 + line_index * 30),
                text,
                fontsize=font_size,
                fontname=font_name,
            )
    pdf.save(pdf_path)
    pdf.close()
    return pdf_path


@pytest.mark.parametrize("text", ["第一章 总则", "2 术语和符号"])
def test_chapter_recognition(text: str) -> None:
    result = StructureParser().parse(make_document(text))

    assert result.blocks[0].role == StructureRole.CHAPTER


def test_section_recognition_does_not_match_clause() -> None:
    result = StructureParser().parse(make_document("4.2 材料", "4.1.1 条文"))

    assert result.blocks[0].role == StructureRole.SECTION
    assert result.blocks[1].role == StructureRole.CLAUSE


def test_clause_recognition_captures_clause_number() -> None:
    result = StructureParser().parse(make_document("4.2.3 混凝土强度等级……"))

    assert result.blocks[0].role == StructureRole.CLAUSE
    assert result.blocks[0].clause_number == "4.2.3"


def test_paragraph_inherits_current_clause_number() -> None:
    result = StructureParser().parse(make_document("4.2.3 条文标题", "后续条文内容。"))

    assert result.blocks[1].clause_number == "4.2.3"
    assert result.blocks[1].section_path[-1] == "4.2.3"


def test_large_bold_first_block_is_document_title() -> None:
    document = make_document("工程规范名称")
    document.pages[0].blocks[0].font_size = 20
    document.pages[0].blocks[0].is_bold = True

    result = StructureParser().parse(document)

    assert result.blocks[0].role == StructureRole.DOCUMENT_TITLE


def test_hierarchy_path_contains_chapter_section_and_clause() -> None:
    result = StructureParser().parse(
        make_document("4 基本设计规定", "4.2 材料", "4.2.3 混凝土……")
    )

    assert result.blocks[2].section_path == [
        "4 基本设计规定",
        "4.2 材料",
        "4.2.3",
    ]


def test_explanation_mode_continues_until_new_top_level_heading() -> None:
    result = StructureParser().parse(
        make_document("条文说明", "4.2.3 条文说明……", "第五章 施工", "正文")
    )

    assert result.blocks[0].role == StructureRole.EXPLANATION_HEADING
    assert result.blocks[1].is_explanation is True
    assert result.blocks[2].is_explanation is False
    assert result.blocks[3].is_explanation is False


@pytest.mark.parametrize("text", ["注：……", "注1：……", "注 2：……"])
def test_note_recognition(text: str) -> None:
    result = StructureParser().parse(make_document(text))

    assert result.blocks[0].role == StructureRole.NOTE


def test_appendix_and_appendix_section_recognition() -> None:
    result = StructureParser().parse(make_document("附录 A", "A.1 材料性能"))

    assert result.blocks[0].role == StructureRole.APPENDIX
    assert result.blocks[1].role == StructureRole.APPENDIX_SECTION
    assert result.blocks[1].section_path == ["附录 A", "A.1 材料性能"]


def test_plain_text_is_paragraph_and_unrecognized_number_is_unknown() -> None:
    result = StructureParser().parse(make_document("这是一段普通正文。", "5.2.1a 扩展编号"))

    assert result.blocks[0].role == StructureRole.PARAGRAPH
    assert result.blocks[1].role == StructureRole.UNKNOWN
    assert result.blocks[1].text == "5.2.1a 扩展编号"


def test_style_metadata_is_extracted_from_pdf_spans(structured_five_page_pdf: Path) -> None:
    document = PdfParser().parse(structured_five_page_pdf)
    title = document.pages[0].blocks[0]

    assert title.text.strip() == "Engineering Standard"
    assert title.font_size == pytest.approx(20)
    assert title.font_name
    assert title.is_bold is True


def test_structure_levels_continue_across_pages(structured_five_page_pdf: Path) -> None:
    structure = StructureParser().parse(PdfParser().parse(structured_five_page_pdf))
    page_three_clause = next(
        block for block in structure.blocks if block.text.strip().startswith("4.2.3")
    )

    assert page_three_clause.page_number == 3
    assert page_three_clause.section_path == [
        "4 基本设计规定",
        "4.2 材料",
        "4.2.3",
    ]


def test_structure_model_serializes_roles_as_json_strings(structured_five_page_pdf: Path) -> None:
    structure = StructureParser().parse(PdfParser().parse(structured_five_page_pdf))

    decoded = json.loads(structure.model_dump_json())

    assert isinstance(structure, DocumentStructure)
    assert decoded["blocks"][0]["role"] in {role.value for role in StructureRole}


def test_parse_structure_cli_outputs_json(structured_five_page_pdf: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/parse_structure.py", str(structured_five_page_pdf)],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    assert json.loads(result.stdout)["document_id"] == "structure-sample"
