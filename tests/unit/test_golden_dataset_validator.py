from engineering_rag.evaluation.dataset import GoldenDataset
from engineering_rag.evaluation.validator import (
    GoldenDatasetValidator,
    ValidationStatus,
)
from engineering_rag.models import Chunk


def chunk(
    chunk_id: str,
    *,
    document_id: str = "doc",
    clause_number: str = "3.2.2",
    is_explanation: bool = False,
    logical_chunk_id: str = "logical-body",
    content_type: str = "clause",
) -> Chunk:
    return Chunk(
        chunk_id=chunk_id,
        document_id=document_id,
        content="有效条文内容",
        page_start=1,
        page_end=1,
        clause_number=clause_number,
        content_type=content_type,
        is_explanation=is_explanation,
        logical_chunk_id=logical_chunk_id,
        source_block_ids=[f"p1_{chunk_id}"],
    )


def dataset(*targets: dict) -> GoldenDataset:
    return GoldenDataset.model_validate(
        {
            "version": "v1",
            "queries": [
                {
                    "query_id": "q1",
                    "query": "结构缝要求？",
                    "query_type": "simple",
                    "relevant": list(targets),
                }
            ],
        }
    )


def target(**updates) -> dict:
    value = {
        "document_id": "doc",
        "clause_number": "3.2.2",
        "is_explanation": False,
        "relevance": 2,
    }
    value.update(updates)
    return value


def test_valid_target_can_match_multiple_physical_chunks_of_one_logical_clause() -> None:
    report = GoldenDatasetValidator().validate(
        dataset(target()),
        [chunk("part-a"), chunk("part-b")],
    )

    assert report.is_valid is True
    assert report.valid_targets == 1
    assert report.results[0].matching_chunk_ids == ["part-a", "part-b"]


def test_document_not_found_is_reported_without_silent_rewrite() -> None:
    report = GoldenDatasetValidator().validate(
        dataset(target(document_id="wrong-document")), [chunk("c1")]
    )

    assert report.is_valid is False
    assert report.results[0].status == ValidationStatus.DOCUMENT_NOT_FOUND
    assert "Available document_id: doc" in report.results[0].suggestions


def test_clause_and_explanation_mismatches_are_distinct() -> None:
    chunks = [chunk("c1")]
    missing = GoldenDatasetValidator().validate(
        dataset(target(clause_number="9.9.9")), chunks
    )
    explanation = GoldenDatasetValidator().validate(
        dataset(target(is_explanation=True)), chunks
    )

    assert missing.results[0].status == ValidationStatus.CLAUSE_NOT_FOUND
    assert explanation.results[0].status == ValidationStatus.EXPLANATION_MISMATCH


def test_duplicate_target_is_invalid() -> None:
    value = target()
    report = GoldenDatasetValidator().validate(
        dataset(value, value.copy()), [chunk("c1")]
    )

    assert report.valid_targets == 1
    assert report.invalid_targets == 1
    assert report.results[1].status == ValidationStatus.DUPLICATE_TARGET


def test_multiple_logical_sources_are_ambiguous() -> None:
    report = GoldenDatasetValidator().validate(
        dataset(target()),
        [
            chunk("c1", logical_chunk_id="logical-a"),
            chunk("c2", logical_chunk_id="logical-b"),
        ],
    )

    assert report.results[0].status == ValidationStatus.AMBIGUOUS_TARGET


def test_content_type_is_checked_when_annotated() -> None:
    report = GoldenDatasetValidator().validate(
        dataset(target(content_type="formula")), [chunk("c1")]
    )

    assert report.results[0].status == ValidationStatus.CONTENT_TYPE_MISMATCH
