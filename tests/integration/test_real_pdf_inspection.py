import json
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest


@pytest.fixture
def inspection_pdf(tmp_path: Path) -> Path:
    pdf_path = tmp_path / "inspection-sample.pdf"
    pdf = pymupdf.open()
    pages = [
        ["第一章 总则", "1.0.1 本标准适用于工程设计。"],
        ["4 基本设计规定", "4.2 材料"],
        ["4.2.3 混凝土强度等级应符合规定。这是长度足够的第二段，用于终端截断测试。"],
        ["条文说明", "4.2.3 本条主要考虑工程安全。"],
    ]
    for lines in pages:
        page = pdf.new_page()
        for index, text in enumerate(lines):
            page.insert_text((72, 72 + index * 34), text, fontname="china-s")
    pdf.save(pdf_path)
    pdf.close()
    return pdf_path


def run_inspector(pdf_path: Path, output_dir: Path, *extra: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/inspect_real_pdf.py",
            str(pdf_path),
            "--standard-name",
            "混凝土结构设计规范",
            "--standard-code",
            "GB 50010-2010",
            "--output-dir",
            str(output_dir),
            *extra,
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_real_pdf_inspection_cli_exports_complete_pipeline(
    inspection_pdf: Path,
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "inspection-output"
    result = run_inspector(inspection_pdf, output_dir, "--max-chunks", "1", "--content-chars", "10")

    assert result.returncode == 0
    assert "Engineering RAG PDF Inspection" in result.stdout
    assert result.stdout.count("[Chunk ") == 1
    assert "..." in result.stdout
    assert result.stderr == ""

    expected = {
        "summary.json",
        "document.json",
        "structure.json",
        "chunks.json",
        "chunks.md",
        "raw_text.txt",
    }
    assert {path.name for path in output_dir.iterdir()} == expected

    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    document = json.loads((output_dir / "document.json").read_text(encoding="utf-8"))
    structure = json.loads((output_dir / "structure.json").read_text(encoding="utf-8"))
    chunks = json.loads((output_dir / "chunks.json").read_text(encoding="utf-8"))

    assert summary["page_count"] == 4
    assert summary["text_pages"] == 4
    assert summary["possible_scanned_pdf"] is False
    assert summary["chunk_count"] == len(chunks)
    assert all(
        key in summary["content_type_counts"]
        for key in ("clause", "paragraph", "note", "explanation", "table", "formula")
    )
    assert all(key in summary for key in ("parse_time_ms", "structure_time_ms", "chunk_time_ms", "total_time_ms"))
    assert document["standard_name"] == "混凝土结构设计规范"
    assert document["standard_code"] == "GB 50010-2010"
    assert structure["standard_name"] == "混凝土结构设计规范"
    assert structure["standard_code"] == "GB 50010-2010"
    assert any(chunk["content_type"] == "clause" for chunk in chunks)
    assert any(chunk["content_type"] == "explanation" for chunk in chunks)
    assert all("logical_chunk_id" in chunk for chunk in chunks)
    assert "===== PAGE 1 =====" in (output_dir / "raw_text.txt").read_text(encoding="utf-8")
    markdown = (output_dir / "chunks.md").read_text(encoding="utf-8")
    assert "## Chunk 001" in markdown
    assert "### Embedding Text" in markdown


def test_inspector_marks_empty_text_pdf_as_possible_scan(tmp_path: Path) -> None:
    pdf_path = tmp_path / "blank.pdf"
    output_dir = tmp_path / "blank-output"
    pdf = pymupdf.open()
    pdf.new_page()
    pdf.save(pdf_path)
    pdf.close()

    result = subprocess.run(
        [sys.executable, "scripts/inspect_real_pdf.py", str(pdf_path), "--output-dir", str(output_dir)],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert "Possible scanned PDF: YES" in result.stdout
    assert "WARNING: PDF may be scanned or have insufficient text layer." in result.stdout
    summary = json.loads((output_dir / "summary.json").read_text(encoding="utf-8"))
    assert summary["possible_scanned_pdf"] is True
    assert summary["text_pages"] == 0


def test_inspector_reports_missing_pdf(tmp_path: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/inspect_real_pdf.py", str(tmp_path / "missing.pdf")],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode != 0
    assert result.stdout == ""
    assert "ERROR: PDF file does not exist" in result.stderr
