from engineering_rag.models import Chunk
from engineering_rag.retrieval.index_validation import validate_index_dataset
from engineering_rag.retrieval.indexer import (
    CHUNK_MAPPING_VERSION,
    chunk_dataset_fingerprint,
)


def chunk(chunk_id: str) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id="doc",
        content=f"content {chunk_id}",
        page_start=1,
        page_end=1,
        content_type="paragraph",
    )


class FakeIndices:
    def __init__(self, metadata: dict[str, str]) -> None:
        self.metadata = metadata

    def get_mapping(self, *, index: str):
        return {index: {"mappings": {"_meta": self.metadata}}}


class FakeClient:
    def __init__(self, count: int, metadata: dict[str, str]) -> None:
        self.value = count
        self.indices = FakeIndices(metadata)

    def count(self, *, index: str):
        return {"count": self.value}


def test_chunk_fingerprint_is_deterministic_across_input_order() -> None:
    assert chunk_dataset_fingerprint([chunk("a"), chunk("b")]) == (
        chunk_dataset_fingerprint([chunk("b"), chunk("a")])
    )


def test_index_validation_requires_count_fingerprint_and_mapping_version() -> None:
    chunks = [chunk("a"), chunk("b")]
    metadata = {
        "chunk_count": "2",
        "chunk_fingerprint": chunk_dataset_fingerprint(chunks),
        "mapping_version": CHUNK_MAPPING_VERSION,
    }

    valid = validate_index_dataset(FakeClient(2, metadata), "index", chunks)
    invalid = validate_index_dataset(FakeClient(1, {}), "index", chunks)

    assert valid.is_valid is True
    assert invalid.is_valid is False
    assert len(invalid.errors) == 4
