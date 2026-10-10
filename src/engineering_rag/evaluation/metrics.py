"""Logical-source retrieval metrics for ranked Chunk results."""

from __future__ import annotations

import math
from collections.abc import Sequence

from engineering_rag.evaluation.dataset import RelevanceTarget
from engineering_rag.retrieval.schemas import RetrievalResult


def recall_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    return logical_recall_at_k(results, targets, k)


def precision_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    return logical_precision_at_k(results, targets, k)


def hit_rate_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    return logical_hit_rate_at_k(results, targets, k)


def mrr_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    return logical_mrr_at_k(results, targets, k)


def ndcg_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    return logical_ndcg_at_k(results, targets, k)


def physical_recall_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    gains, relevant_count = _ranked_gains(results, targets, k, deduplicate=False)
    return sum(gain > 0 for gain in gains) / relevant_count


def logical_recall_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    gains, relevant_count = _ranked_gains(results, targets, k, deduplicate=True)
    return sum(gain > 0 for gain in gains) / relevant_count


def physical_precision_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    gains, _ = _ranked_gains(results, targets, k, deduplicate=False)
    return sum(gain > 0 for gain in gains) / k


def logical_precision_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    gains, _ = _ranked_gains(results, targets, k, deduplicate=True)
    return sum(gain > 0 for gain in gains) / k


def physical_hit_rate_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    gains, _ = _ranked_gains(results, targets, k, deduplicate=False)
    return float(any(gain > 0 for gain in gains))


def logical_hit_rate_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    gains, _ = _ranked_gains(results, targets, k, deduplicate=True)
    return float(any(gain > 0 for gain in gains))


def physical_mrr_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    return _mrr(results, targets, k, deduplicate=False)


def logical_mrr_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    return _mrr(results, targets, k, deduplicate=True)


def physical_ndcg_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    return _ndcg(results, targets, k, deduplicate=False)


def logical_ndcg_at_k(
    results: Sequence[RetrievalResult], targets: Sequence[RelevanceTarget], k: int
) -> float:
    return _ndcg(results, targets, k, deduplicate=True)


def logical_result_count(results: Sequence[RetrievalResult]) -> int:
    """Count distinct logical sources in a physical candidate list."""

    return len({_result_key(result) for result in results})


def _mrr(
    results: Sequence[RetrievalResult],
    targets: Sequence[RelevanceTarget],
    k: int,
    *,
    deduplicate: bool,
) -> float:
    gains, _ = _ranked_gains(results, targets, k, deduplicate=deduplicate)
    for rank, gain in enumerate(gains, start=1):
        if gain > 0:
            return 1.0 / rank
    return 0.0


def _ndcg(
    results: Sequence[RetrievalResult],
    targets: Sequence[RelevanceTarget],
    k: int,
    *,
    deduplicate: bool,
) -> float:
    gains, _ = _ranked_gains(results, targets, k, deduplicate=deduplicate)
    dcg = _dcg(gains)
    ideal_gains = sorted(
        (_maximum_target_relevance(targets).values()), reverse=True
    )[:k]
    ideal_dcg = _dcg(ideal_gains)
    return dcg / ideal_dcg if ideal_dcg else 0.0


def _ranked_gains(
    results: Sequence[RetrievalResult],
    targets: Sequence[RelevanceTarget],
    k: int,
    *,
    deduplicate: bool = True,
) -> tuple[list[int], int]:
    if k < 1:
        raise ValueError("k must be at least 1")
    positive_targets = [target for target in targets if target.relevance > 0]
    target_relevance = _maximum_target_relevance(positive_targets)
    if not target_relevance:
        raise ValueError("At least one positive relevance target is required")

    ranked_results: list[RetrievalResult] = []
    seen_result_keys: set[tuple[object, ...]] = set()
    for result in results:
        key = _result_key(result)
        if deduplicate and key in seen_result_keys:
            continue
        seen_result_keys.add(key)
        ranked_results.append(result)
        if len(ranked_results) == k:
            break

    matched_targets: set[tuple[object, ...]] = set()
    gains: list[int] = []
    for result in ranked_results:
        candidates = [
            (key, relevance)
            for key, relevance in target_relevance.items()
            if key not in matched_targets
            and _target_matches_result(key, result)
        ]
        if not candidates:
            gains.append(0)
            continue
        key, relevance = max(candidates, key=lambda item: item[1])
        matched_targets.add(key)
        gains.append(relevance)
    return gains, len(target_relevance)


def _maximum_target_relevance(
    targets: Sequence[RelevanceTarget],
) -> dict[tuple[object, ...], int]:
    relevance: dict[tuple[object, ...], int] = {}
    for target in targets:
        if target.relevance <= 0:
            continue
        key = _target_key(target)
        relevance[key] = max(relevance.get(key, 0), target.relevance)
    return relevance


def _target_key(target: RelevanceTarget) -> tuple[object, ...]:
    base = (target.document_id, target.is_explanation, target.content_type)
    if target.clause_number:
        return ("clause", *base, target.clause_number)
    if target.logical_chunk_id:
        return ("logical", *base, target.logical_chunk_id)
    return ("source", *base, tuple(sorted(target.source_block_ids)))


def _result_key(result: RetrievalResult) -> tuple[object, ...]:
    base = (result.document_id, result.is_explanation, result.content_type)
    if result.clause_number:
        return ("clause", *base, result.clause_number)
    if result.logical_chunk_id:
        return ("logical", *base, result.logical_chunk_id)
    if result.source_block_ids:
        return ("source", *base, tuple(sorted(result.source_block_ids)))
    return ("chunk", result.chunk_id)


def _target_matches_result(
    target_key: tuple[object, ...], result: RetrievalResult
) -> bool:
    kind, document_id, is_explanation, content_type, locator = target_key
    if document_id != result.document_id or is_explanation != result.is_explanation:
        return False
    if content_type is not None and content_type != result.content_type:
        return False
    if kind == "clause":
        return locator == result.clause_number
    if kind == "logical":
        return locator == result.logical_chunk_id
    return locator == tuple(sorted(result.source_block_ids))


def _dcg(gains: Sequence[int]) -> float:
    return sum(
        ((2**gain) - 1) / math.log2(rank + 1)
        for rank, gain in enumerate(gains, start=1)
    )
