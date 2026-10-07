import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

from engineering_rag.ingestion.parser import Document, PdfParseError, PdfParser


@pytest.fixture
def two_page_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "GB50010-2010.pdf"
    pdf = pymupdf.open()
    first = pdf.new_page()
    first.insert_text((72, 72), "第一章 总则", fontname="china-s")
    second = pdf.new_page()
    second.insert_text((72, 72), "1.0.1 本标准适用于……。", fontname="china-s")
    pdf.save(pdf_path)
    pdf.close()
    return pdf_path


def test_parse_two_page_pdf_and_extract_text(two_page_pdf: Path) -> None:
    document = PdfParser().parse(two_page_pdf)

    assert isinstance(document, Document)
    assert document.document_id == "GB50010-2010"
    assert document.page_count == 2
    assert [page.page_number for page in document.pages] == [1, 2]
    assert "第一章 总则" in document.pages[0].text
    assert "1.0.1 本标准适用于" in document.pages[1].text


def test_text_block_has_text_bbox_number_and_type(two_page_pdf: Path) -> None:
    document = PdfParser().parse(two_page_pdf)
    block = document.pages[0].blocks[0]

    assert block.text.strip() == "第一章 总则"
    assert len(block.bbox) == 4
    assert all(isinstance(coordinate, (int, float)) for coordinate in block.bbox)
    assert block.block_number == 0
    assert isinstance(block.block_type, int)


def test_page_numbers_are_one_based_and_in_order(tmp_path: Path) -> None:
    pdf_path = tmp_path / "three-pages.pdf"
    pdf = pymupdf.open()
    for page_number in range(1, 4):
        pdf.new_page().insert_text((72, 72), f"Page {page_number}")
    pdf.save(pdf_path)
    pdf.close()

    document = PdfParser().parse(pdf_path)

    assert [page.page_number for page in document.pages] == [1, 2, 3]


def test_blank_page_is_supported(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    pdf = pymupdf.open()
    pdf.new_page()
    pdf.save(pdf_path)
    pdf.close()

    document = PdfParser().parse(pdf_path)

    assert document.page_count == 1
    assert document.pages[0].text == ""
    assert document.pages[0].blocks == []


def test_missing_pdf_has_clear_exception(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.pdf"

    with pytest.raises(FileNotFoundError, match="PDF file does not exist"):
        PdfParser().parse(missing_path)


def test_invalid_pdf_has_clear_exception(tmp_path: Path) -> None:
    invalid_path = tmp_path / "broken.pdf"
    invalid_path.write_text("not a PDF", encoding="utf-8")

    with pytest.raises(PdfParseError, match="Unable to open PDF"):
        PdfParser().parse(invalid_path)


def test_document_serializes_to_json(two_page_pdf: Path) -> None:
    document = PdfParser().parse(two_page_pdf)

    decoded = json.loads(document.model_dump_json())

    assert decoded["page_count"] == 2
    assert decoded["pages"][0]["page_number"] == 1


def test_parser_preserves_caller_supplied_standard_metadata(two_page_pdf: Path) -> None:
    document = PdfParser().parse(
        two_page_pdf,
        standard_name="Engineering Standard",
        standard_code="STD-001",
    )

    assert document.standard_name == "Engineering Standard"
    assert document.standard_code == "STD-001"


def test_cli_prints_valid_json(two_page_pdf: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/parse_pdf.py", str(two_page_pdf)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stderr == ""
    decoded = json.loads(result.stdout)
    assert decoded["page_count"] == 2


def test_cli_writes_json_to_output_file(two_page_pdf: Path, tmp_path: Path) -> None:
    output_path = tmp_path / "result.json"
    result = subprocess.run(
        [sys.executable, "scripts/parse_pdf.py", str(two_page_pdf), "--output", str(output_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout == ""
    assert json.loads(output_path.read_text(encoding="utf-8"))["page_count"] == 2


def test_cli_reports_errors_to_stderr(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.pdf"
    result = subprocess.run(
        [sys.executable, "scripts/parse_pdf.py", str(missing_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "PDF file does not exist" in result.stderr


def test_cli_reports_invalid_pdf_to_stderr(tmp_path: Path) -> None:
    invalid_path = tmp_path / "broken.pdf"
    invalid_path.write_text("not a PDF", encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/parse_pdf.py", str(invalid_path)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "Unable to open PDF" in result.stderr
    assert "Traceback" not in result.stderr
