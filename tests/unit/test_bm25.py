from pathlib import Path

import pytest

from engineering_rag.models import Chunk
from engineering_rag.retrieval.bm25 import BM25Retriever
from engineering_rag.retrieval.indexer import (
    CHUNK_INDEX_MAPPING,
    ElasticsearchChunkIndexer,
    load_chunks,
)


def make_chunk(chunk_id: str = "c1", **updates) -> Chunk:
    values = {
        "chunk_id": chunk_id,
        "logical_chunk_id": "doc-4.2.3-body",
        "document_id": "doc",
        "content": "4.2.3 混凝土强度等级应符合规定。",
        "page_start": 4,
        "page_end": 4,
        "standard_name": "混凝土结构设计规范",
        "standard_code": "GB 50010-2010",
        "clause_number": "4.2.3",
        "section_path": ["4 基本设计规定", "4.2 材料", "4.2.3"],
        "content_type": "clause",
        "source_block_ids": ["p4_block_1"],
        "context_header": "混凝土结构设计规范 > 4.2 材料",
    }
    values.update(updates)
    return Chunk(**values)


class FakeIndices:
    def __init__(self, exists: bool = False) -> None:
        self.exists_value = exists
        self.created = []
        self.deleted = []

    def exists(self, *, index: str) -> bool:
        return self.exists_value

    def create(self, **kwargs) -> None:
        self.created.append(kwargs)

    def delete(self, *, index: str) -> None:
        self.deleted.append(index)


class FakeClient:
    def __init__(self, *, index_exists: bool = False) -> None:
        self.indices = FakeIndices(index_exists)
        self.bulk_calls = []
        self.search_calls = []
        self.bulk_response = {"items": []}
        self.search_response = {"hits": {"hits": []}}

    def bulk(self, **kwargs):
        self.bulk_calls.append(kwargs)
        return self.bulk_response

    def search(self, **kwargs):
        self.search_calls.append(kwargs)
        return self.search_response


def test_mapping_contains_required_explicit_field_types() -> None:
    properties = CHUNK_INDEX_MAPPING["properties"]

    assert CHUNK_INDEX_MAPPING["dynamic"] == "strict"
    assert properties["chunk_id"]["type"] == "keyword"
    assert properties["logical_chunk_id"]["type"] == "keyword"
    assert properties["content"]["type"] == "text"
    assert properties["standard_name"]["fields"]["keyword"]["type"] == "keyword"
    assert properties["is_explanation"]["type"] == "boolean"
    assert properties["page_start"]["type"] == "integer"
    assert "dense_vector" not in {value["type"] for value in properties.values()}


def test_create_index_does_not_delete_existing_index_by_default() -> None:
    client = FakeClient(index_exists=True)

    ElasticsearchChunkIndexer(client, "chunks").create_index()

    assert client.indices.deleted == []
    assert client.indices.created == []


def test_create_index_recreates_only_when_explicit() -> None:
    client = FakeClient(index_exists=True)

    ElasticsearchChunkIndexer(client, "chunks").create_index(recreate=True)

    assert client.indices.deleted == ["chunks"]
    assert client.indices.created[0]["mappings"] == CHUNK_INDEX_MAPPING


def test_bulk_index_uses_chunk_id_as_id_and_preserves_metadata() -> None:
    client = FakeClient()
    client.bulk_response = {"items": [{"index": {"status": 201}}]}
    chunk = make_chunk()

    result = ElasticsearchChunkIndexer(client, "chunks", refresh=True).index_chunks([chunk])

    operations = client.bulk_calls[0]["operations"]
    assert operations[0] == {"index": {"_index": "chunks", "_id": "c1"}}
    assert operations[1]["source_block_ids"] == ["p4_block_1"]
    assert operations[1]["content"] == chunk.content
    assert client.bulk_calls[0]["refresh"] is True
    assert result.success_count == 1
    assert result.failure_count == 0


def test_bulk_index_empty_input_is_a_noop() -> None:
    client = FakeClient()

    result = ElasticsearchChunkIndexer(client, "chunks").index_chunks([])

    assert result.success_count == 0
    assert result.failure_count == 0
    assert client.bulk_calls == []


def test_bulk_index_returns_partial_failure_details() -> None:
    client = FakeClient()
    client.bulk_response = {
        "items": [
            {"index": {"status": 201}},
            {"index": {"status": 400, "error": {"reason": "bad field"}}},
        ]
    }

    result = ElasticsearchChunkIndexer(client, "chunks").index_chunks(
        [make_chunk("c1"), make_chunk("c2")]
    )

    assert result.success_count == 1
    assert result.failure_count == 1
    assert result.errors[0].chunk_id == "c2"
    assert result.errors[0].reason == "bad field"


def test_load_chunks_accepts_task_4_2_json(tmp_path: Path) -> None:
    path = tmp_path / "chunks.json"
    path.write_text(f"[{make_chunk().model_dump_json()}]", encoding="utf-8")

    chunks = load_chunks(path)

    assert chunks == [make_chunk()]


def test_query_dsl_uses_configurable_weights_and_structured_filters() -> None:
    client = FakeClient()
    retriever = BM25Retriever(
        client,
        "chunks",
        field_weights={"content": 4.0, "context_header": 1.5},
    )

    query = retriever.build_query(
        "强度等级",
        {
            "standard_code": "GB 50010-2010",
            "clause_number": "4.2.3",
            "is_explanation": False,
        },
    )

    multi_match = query["bool"]["must"][0]["multi_match"]
    assert multi_match["fields"] == ["content^4", "context_header^1.5"]
    assert {"term": {"standard_code": "GB 50010-2010"}} in query["bool"]["filter"]
    assert {"term": {"clause_number": "4.2.3"}} in query["bool"]["filter"]
    assert {"term": {"is_explanation": False}} in query["bool"]["filter"]


@pytest.mark.parametrize("query", ["", "   "])
def test_empty_query_is_rejected(query: str) -> None:
    with pytest.raises(ValueError, match="query must not be empty"):
        BM25Retriever(FakeClient(), "chunks").search(query)


def test_invalid_filter_and_top_k_are_rejected() -> None:
    retriever = BM25Retriever(FakeClient(), "chunks")

    with pytest.raises(ValueError, match="Unsupported"):
        retriever.search("query", filters={"unknown": "x"})
    with pytest.raises(ValueError, match="top_k"):
        retriever.search("query", top_k=0)


def test_search_maps_ranked_hits_to_retrieval_results() -> None:
    client = FakeClient()
    first = make_chunk("c1").model_dump(mode="json")
    second = make_chunk("c2", clause_number="4.2.4").model_dump(mode="json")
    client.search_response = {
        "hits": {
            "hits": [
                {"_id": "c2", "_score": 3.0, "_source": second},
                {"_id": "c1", "_score": 8.0, "_source": first},
            ]
        }
    }

    results = BM25Retriever(client, "chunks").search("混凝土", top_k=2)

    assert [result.rank for result in results] == [1, 2]
    assert [result.score for result in results] == [8.0, 3.0]
    assert [result.chunk_id for result in results] == ["c1", "c2"]
    assert client.search_calls[0]["size"] == 2
