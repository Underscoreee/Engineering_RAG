import pytest
from pydantic import ValidationError

from engineering_rag import Chunk


def valid_chunk_data() -> dict:
    return {
        "chunk_id": "chunk-1",
        "document_id": "standard-1",
        "content": "Requirements for structural design.",
        "page_start": 3,
        "page_end": 4,
        "standard_name": "Structural Standard",
        "standard_code": "STD-001",
        "clause_number": "2.1",
        "section_path": ["Design", "Loads"],
        "content_type": "requirement",
        "is_mandatory": True,
        "is_explanation": False,
    }


def test_chunk_can_be_created_with_valid_data() -> None:
    chunk = Chunk(**valid_chunk_data())

    assert chunk.chunk_id == "chunk-1"
    assert chunk.page_start == 3
    assert chunk.section_path == ["Design", "Loads"]


@pytest.mark.parametrize("field", ["chunk_id", "document_id", "content", "page_start", "page_end", "content_type"])
def test_required_fields_are_required(field: str) -> None:
    data = valid_chunk_data()
    del data[field]

    with pytest.raises(ValidationError):
        Chunk(**data)


def test_optional_metadata_and_boolean_fields_have_defaults() -> None:
    chunk = Chunk(
        chunk_id="chunk-1",
        document_id="standard-1",
        content="Some text",
        page_start=1,
        page_end=1,
        content_type="body",
    )

    assert chunk.standard_name is None
    assert chunk.standard_code is None
    assert chunk.clause_number is None
    assert chunk.section_path == []
    assert chunk.is_mandatory is False
    assert chunk.is_explanation is False


@pytest.mark.parametrize(
    "updates",
    [
        {"chunk_id": ""},
        {"content": ""},
        {"page_start": 0},
        {"page_end": 0},
        {"page_start": 5, "page_end": 4},
        {"content_type": ""},
        {"unexpected": "field"},
    ],
)
def test_invalid_types_or_values_are_rejected(updates: dict) -> None:
    data = valid_chunk_data()
    data.update(updates)

    with pytest.raises(ValidationError):
        Chunk(**data)


def test_section_path_is_a_list_of_strings() -> None:
    data = valid_chunk_data()
    data["section_path"] = ["Chapter 1", 2]

    with pytest.raises(ValidationError):
        Chunk(**data)


def test_mandatory_and_explanation_flags_are_preserved() -> None:
    chunk = Chunk(**valid_chunk_data())

    assert chunk.is_mandatory is True
    assert chunk.is_explanation is False
