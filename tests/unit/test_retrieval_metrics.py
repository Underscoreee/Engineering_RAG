import math

import pytest

from engineering_rag.evaluation.dataset import RelevanceTarget
from engineering_rag.evaluation.metrics import (
    hit_rate_at_k,
    mrr_at_k,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
)
from engineering_rag.retrieval.schemas import RetrievalResult


def target(
    document_id: str = "doc-a",
    clause_number: str | None = "4.2.3",
    *,
    is_explanation: bool = False,
    relevance: int = 2,
    logical_chunk_id: str | None = None,
) -> RelevanceTarget:
    return RelevanceTarget(
        document_id=document_id,
        clause_number=clause_number,
        is_explanation=is_explanation,
        relevance=relevance,
        logical_chunk_id=logical_chunk_id,
    )


def result(
    chunk_id: str,
    document_id: str = "doc-a",
    clause_number: str | None = "4.2.3",
    *,
    is_explanation: bool = False,
    content_type: str = "clause",
    logical_chunk_id: str | None = None,
    source_block_ids: list[str] | None = None,
) -> RetrievalResult:
    return RetrievalResult(
        chunk_id=chunk_id,
        document_id=document_id,
        content="text",
        score=1.0,
        rank=1,
        clause_number=clause_number,
        section_path=[],
        page_start=1,
        page_end=1,
        content_type=content_type,
        is_explanation=is_explanation,
        logical_chunk_id=logical_chunk_id,
        source_block_ids=source_block_ids or [],
    )


def test_complete_hit_and_complete_miss() -> None:
    relevant = [target()]

    assert recall_at_k([result("c1")], relevant, 1) == 1.0
    assert precision_at_k([result("c1")], relevant, 1) == 1.0
    assert hit_rate_at_k([result("c1")], relevant, 1) == 1.0
    assert mrr_at_k([result("c1")], relevant, 1) == 1.0
    assert ndcg_at_k([result("c1")], relevant, 1) == 1.0

    miss = [result("c2", document_id="other")]
    assert recall_at_k(miss, relevant, 1) == 0.0
    assert hit_rate_at_k(miss, relevant, 1) == 0.0
    assert mrr_at_k(miss, relevant, 1) == 0.0
    assert ndcg_at_k(miss, relevant, 1) == 0.0


def test_multiple_relevant_targets_and_k_larger_than_results() -> None:
    relevant = [target(clause_number="1.0.1"), target(clause_number="1.0.2")]
    results = [result("c1", clause_number="1.0.1")]

    assert recall_at_k(results, relevant, 10) == 0.5
    assert precision_at_k(results, relevant, 10) == 0.1
    assert hit_rate_at_k(results, relevant, 10) == 1.0


def test_duplicate_physical_chunks_do_not_inflate_logical_recall() -> None:
    relevant = [target(clause_number="1.0.1"), target(clause_number="1.0.2")]
    results = [
        result("part-a", clause_number="1.0.1"),
        result("part-b", clause_number="1.0.1"),
    ]

    assert recall_at_k(results, relevant, 2) == 0.5
    assert precision_at_k(results, relevant, 2) == 0.5


def test_same_clause_in_different_document_does_not_match() -> None:
    assert recall_at_k(
        [result("c1", document_id="doc-b")],
        [target(document_id="doc-a")],
        1,
    ) == 0.0


def test_normative_and_explanation_with_same_clause_are_distinct() -> None:
    explanation = [target(is_explanation=True)]

    assert recall_at_k([result("body", is_explanation=False)], explanation, 1) == 0.0
    assert recall_at_k([result("explain", is_explanation=True)], explanation, 1) == 1.0


def test_empty_results_are_valid_but_empty_relevance_is_not() -> None:
    assert recall_at_k([], [target()], 5) == 0.0
    assert precision_at_k([], [target()], 5) == 0.0
    assert hit_rate_at_k([], [target()], 5) == 0.0

    with pytest.raises(ValueError, match="positive relevance"):
        recall_at_k([], [], 5)


def test_mrr_uses_first_relevant_rank_after_logical_deduplication() -> None:
    results = [
        result("miss", document_id="other"),
        result("hit"),
    ]
    assert mrr_at_k(results, [target()], 5) == 0.5


def test_ndcg_supports_graded_relevance() -> None:
    relevant = [
        target(clause_number="1.0.1", relevance=2),
        target(clause_number="1.0.2", relevance=1),
    ]
    reversed_results = [
        result("partial", clause_number="1.0.2"),
        result("high", clause_number="1.0.1"),
    ]
    expected = (1 + 3 / math.log2(3)) / (3 + 1 / math.log2(3))

    assert ndcg_at_k(reversed_results, relevant, 2) == pytest.approx(expected)


def test_no_clause_uses_stable_logical_locator() -> None:
    relevant = [
        target(
            clause_number=None,
            logical_chunk_id="doc-paragraph-7",
            relevance=1,
        )
    ]
    results = [
        result(
            "physical-new-id",
            clause_number=None,
            logical_chunk_id="doc-paragraph-7",
            content_type="paragraph",
        )
    ]

    assert recall_at_k(results, relevant, 1) == 1.0
