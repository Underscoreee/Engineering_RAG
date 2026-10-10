from engineering_rag.evaluation.dataset import RelevanceTarget
from engineering_rag.evaluation.evaluator import RetrievalEvaluator
from engineering_rag.evaluation.metrics import (
    logical_recall_at_k,
    logical_result_count,
    physical_recall_at_k,
)
from engineering_rag.retrieval.schemas import RetrievalResult


def result(chunk_id: str, clause: str, logical_id: str) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id="doc",
        content="text",
        score=1.0,
        rank=1,
        clause_number=clause,
        page_start=1,
        page_end=1,
        content_type="clause",
        logical_chunk_id=logical_id,
    )


def targets() -> list[RelevanceTarget]:
    return [
        RelevanceTarget(
            document_id="doc",
            clause_number=clause,
            relevance=2,
        )
        for clause in ("1.0.1", "1.0.2")
    ]


def test_physical_and_logical_recall_treat_duplicate_chunks_differently() -> None:
    results = [
        result("a-part-1", "1.0.1", "logical-a"),
        result("a-part-2", "1.0.1", "logical-a"),
        result("b", "1.0.2", "logical-b"),
    ]

    assert physical_recall_at_k(results, targets(), 2) == 0.5
    assert logical_recall_at_k(results, targets(), 2) == 1.0
    assert logical_result_count(results) == 2


def test_candidate_pool_shortage_is_recorded() -> None:
    class FakeRetriever:
        index_name = "index"
        query_fields = ["content^3"]
        field_weights = {"content": 3.0}

        def search(self, query: str, top_k: int = 5):
            assert top_k == 50
            return [result("a", "1.0.1", "logical-a")]

    from engineering_rag.evaluation.dataset import GoldenDataset

    dataset = GoldenDataset.model_validate(
        {
            "version": "v1",
            "queries": [
                {
                    "query_id": "q1",
                    "query": "query",
                    "query_type": "simple",
                    "relevant": [targets()[0].model_dump()],
                }
            ],
        }
    )
    report = RetrievalEvaluator(FakeRetriever()).evaluate(dataset)

    assert report["per_query"][0]["logical_candidate_pool_insufficient"] is True
    assert report["metrics"]["physical_recall_at_1"] == 1.0
    assert report["metrics"]["logical_recall_at_1"] == 1.0
