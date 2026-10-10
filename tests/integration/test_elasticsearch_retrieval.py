import os
import uuid

import pytest

pytest.importorskip("elasticsearch", reason="Elasticsearch Python client is not installed")

from engineering_rag.models import Chunk
from engineering_rag.retrieval import BM25Retriever, ElasticsearchChunkIndexer
from engineering_rag.retrieval.elasticsearch_client import (
    ElasticsearchSettings,
    create_elasticsearch_client,
)
from engineering_rag.retrieval.index_validation import validate_index_dataset


def chunk(
    chunk_id: str,
    clause_number: str,
    content: str,
    *,
    standard_code: str = "TEST 100-2026",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        logical_chunk_id=f"test-{clause_number}",
        document_id="task5-test-document",
        content=content,
        page_start=1,
        page_end=1,
        standard_name="Task 5 测试规范",
        standard_code=standard_code,
        clause_number=clause_number,
        section_path=[clause_number],
        content_type="clause",
        source_block_ids=[f"p1-{chunk_id}"],
    )


@pytest.fixture
def elasticsearch_client():
    url = os.getenv("ELASTICSEARCH_URL")
    if not url:
        pytest.skip("ELASTICSEARCH_URL is not set; real Elasticsearch integration test skipped")
    settings = ElasticsearchSettings(
        url=url,
        username=os.getenv("ELASTICSEARCH_USERNAME"),
        password=os.getenv("ELASTICSEARCH_PASSWORD"),
    )
    client = create_elasticsearch_client(settings)
    try:
        client.info()
    except Exception as exc:
        pytest.skip(f"Elasticsearch is unavailable at configured URL: {exc}")
    return client


def test_real_elasticsearch_index_search_filter_order_and_idempotency(
    elasticsearch_client,
) -> None:
    index_name = f"engineering-rag-task5-test-{uuid.uuid4().hex}"
    indexer = ElasticsearchChunkIndexer(
        elasticsearch_client, index_name, refresh=True
    )
    chunks = [
        chunk("test-c1", "4.2.3", "混凝土 强度 等级 混凝土 强度 要求"),
        chunk("test-c2", "5.1.1", "钢筋 构造 一般 规定"),
    ]
    try:
        indexer.create_index()
        first = indexer.index_chunks(chunks, record_dataset_metadata=True)
        second = indexer.index_chunks(chunks, record_dataset_metadata=True)
        assert first.success_count == second.success_count == 2
        assert elasticsearch_client.count(index=index_name)["count"] == 2
        assert validate_index_dataset(
            elasticsearch_client, index_name, chunks
        ).is_valid

        retriever = BM25Retriever(elasticsearch_client, index_name)
        results = retriever.search("混凝土 强度", top_k=2)
        assert results
        assert results[0].chunk_id == "test-c1"
        assert [item.score for item in results] == sorted(
            [item.score for item in results], reverse=True
        )

        filtered = retriever.search(
            "要求",
            top_k=5,
            filters={
                "standard_code": "TEST 100-2026",
                "clause_number": "4.2.3",
                "document_id": "task5-test-document",
                "content_type": "clause",
                "is_explanation": False,
            },
        )
        assert [item.chunk_id for item in filtered] == ["test-c1"]
    finally:
        if elasticsearch_client.indices.exists(index=index_name):
            elasticsearch_client.indices.delete(index=index_name)
