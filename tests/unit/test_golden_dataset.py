import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from engineering_rag.evaluation.dataset import GoldenDataset, load_golden_dataset
from engineering_rag.evaluation.evaluator import RetrievalEvaluator, write_evaluation_report
from engineering_rag.retrieval.schemas import RetrievalResult


def valid_payload() -> dict:
    return {
        "version": "human-v1",
        "queries": [
            {
                "query_id": "q1",
                "query": "强度等级要求？",
                "query_type": "limit",
                "relevant": [
                    {
                        "document_id": "doc",
                        "clause_number": "4.2.3",
                        "is_explanation": False,
                        "relevance": 2,
                    }
                ],
            }
        ],
    }


def result() -> RetrievalResult:
    return RetrievalResult(
        chunk_id="c1",
        document_id="doc",
        content="强度等级要求",
        score=2.0,
        rank=1,
        clause_number="4.2.3",
        section_path=["4.2.3"],
        page_start=1,
        page_end=1,
        content_type="clause",
    )


def test_load_golden_dataset(tmp_path: Path) -> None:
    path = tmp_path / "golden.json"
    path.write_text(json.dumps(valid_payload(), ensure_ascii=False), encoding="utf-8")

    dataset = load_golden_dataset(path)

    assert dataset.version == "human-v1"
    assert dataset.queries[0].query_type == "limit"
    assert dataset.queries[0].relevant[0].relevance == 2


def test_target_without_clause_requires_stable_source_locator() -> None:
    payload = valid_payload()
    payload["queries"][0]["relevant"][0]["clause_number"] = None

    with pytest.raises(ValidationError, match="logical_chunk_id or source_block_ids"):
        GoldenDataset.model_validate(payload)

    payload["queries"][0]["relevant"][0]["logical_chunk_id"] = "doc-paragraph-1"
    assert GoldenDataset.model_validate(payload).queries[0].relevant[0].logical_chunk_id


def test_empty_dataset_and_query_without_positive_target_are_rejected() -> None:
    with pytest.raises(ValidationError):
        GoldenDataset.model_validate({"version": "v1", "queries": []})

    payload = valid_payload()
    payload["queries"][0]["relevant"][0]["relevance"] = 0
    with pytest.raises(ValidationError, match="positive relevance"):
        GoldenDataset.model_validate(payload)


def test_duplicate_query_ids_are_rejected() -> None:
    payload = valid_payload()
    payload["queries"].append(payload["queries"][0].copy())

    with pytest.raises(ValidationError, match="unique"):
        GoldenDataset.model_validate(payload)


class FakeRetriever:
    index_name = "test-index"
    query_fields = ["content^3"]
    field_weights = {"content": 3.0}

    def search(self, query: str, top_k: int = 5):
        assert query
        assert top_k == 50
        return [result()]


def test_evaluator_and_report_include_reproducibility_metadata(tmp_path: Path) -> None:
    report = RetrievalEvaluator(FakeRetriever()).evaluate(
        GoldenDataset.model_validate(valid_payload())
    )
    write_evaluation_report(report, tmp_path)

    metrics = json.loads((tmp_path / "metrics.json").read_text(encoding="utf-8"))
    per_query = json.loads((tmp_path / "per_query.json").read_text(encoding="utf-8"))
    markdown = (tmp_path / "report.md").read_text(encoding="utf-8")
    assert metrics["dataset_version"] == "human-v1"
    assert metrics["index_name"] == "test-index"
    assert metrics["index_configuration"]["ranking"] == "Elasticsearch native BM25"
    assert metrics["field_weights"] == {"content": 3.0}
    assert metrics["metrics"]["physical_recall_at_10"] == 1.0
    assert metrics["metrics"]["logical_recall_at_10"] == 1.0
    assert per_query[0]["query_id"] == "q1"
    assert per_query[0]["relevant"][0]["clause_number"] == "4.2.3"
    assert "Run time" in markdown
