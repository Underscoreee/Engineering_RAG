import os
from pathlib import Path

import pytest

from engineering_rag.chunking import EngineeringChunker
from engineering_rag.ingestion.parser import PdfParser
from engineering_rag.ingestion.structure import StructureParser, StructureRole


def test_configured_real_pdf_structure_and_chunk_ids_are_stable() -> None:
    configured = os.getenv("ENGINEERING_RAG_REAL_PDF")
    if not configured:
        pytest.skip("ENGINEERING_RAG_REAL_PDF is not set")
    pdf_path = Path(configured)
    if not pdf_path.is_file():
        pytest.fail(f"Configured real PDF does not exist: {pdf_path}")

    document = PdfParser().parse(pdf_path)
    structure = StructureParser().parse(document)
    chunks_first = EngineeringChunker().chunk(structure)
    chunks_second = EngineeringChunker().chunk(StructureParser().parse(document))

    for clause_number in ("3.2.2", "3.5.4", "9.1.3"):
        matching = [
            block
            for block in structure.blocks
            if block.role == StructureRole.CLAUSE
            and block.clause_number == clause_number
        ]
        assert {block.is_explanation for block in matching} == {False, True}
    assert [chunk.chunk_id for chunk in chunks_first] == [
        chunk.chunk_id for chunk in chunks_second
    ]
    assert len({chunk.chunk_id for chunk in chunks_first}) == len(chunks_first)
