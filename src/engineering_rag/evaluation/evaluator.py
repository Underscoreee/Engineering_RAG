"""Run BM25 retrieval over a Golden Dataset and write reproducible reports."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean
from typing import Any

from engineering_rag.evaluation.dataset import GoldenDataset, GoldenQuery
from engineering_rag.evaluation.metrics import (
    logical_hit_rate_at_k,
    logical_mrr_at_k,
    logical_ndcg_at_k,
    logical_precision_at_k,
    logical_recall_at_k,
    logical_result_count,
    physical_hit_rate_at_k,
    physical_mrr_at_k,
    physical_ndcg_at_k,
    physical_precision_at_k,
    physical_recall_at_k,
)
from engineering_rag.retrieval.bm25 import BM25Retriever


RECALL_K = (1, 3, 5, 10)
RANKING_K = (5, 10)


class RetrievalEvaluator:
    """Evaluate a retriever without changing its retrieval behavior."""

    def __init__(self, retriever: BM25Retriever, *, candidate_pool: int = 50) -> None:
        if candidate_pool < max(RECALL_K):
            raise ValueError(f"candidate_pool must be at least {max(RECALL_K)}")
        self.retriever = retriever
        self.candidate_pool = candidate_pool

    def evaluate(self, dataset: GoldenDataset) -> dict[str, Any]:
        if not dataset.queries:
            raise ValueError("Golden Dataset must contain at least one query")

        per_query: list[dict[str, Any]] = []
        for query in dataset.queries:
            results = self.retriever.search(
                query.query, top_k=self.candidate_pool
            )
            metrics = self._query_metrics(query, results)
            logical_candidates = logical_result_count(results)
            per_query.append(
                {
                    "query_id": query.query_id,
                    "query": query.query,
                    "query_type": query.query_type,
                    "relevant": [
                        target.model_dump(mode="json") for target in query.relevant
                    ],
                    "metrics": metrics,
                    "candidate_pool_requested": self.candidate_pool,
                    "physical_candidates_returned": len(results),
                    "logical_candidates_returned": logical_candidates,
                    "logical_candidate_pool_insufficient": logical_candidates
                    < max(RECALL_K),
                    "results": [result.model_dump(mode="json") for result in results],
                }
            )

        return {
            "dataset_version": dataset.version,
            "dataset_size": len(dataset.queries),
            "index_name": self.retriever.index_name,
            "index_configuration": {
                "mapping": "engineering_rag_chunks_v1",
                "text_analyzer": "engineering_standard (built-in standard)",
                "ranking": "Elasticsearch native BM25",
            },
            "query_fields": self.retriever.query_fields,
            "field_weights": self.retriever.field_weights,
            "candidate_pool": self.candidate_pool,
            "run_time": datetime.now(timezone.utc).isoformat(),
            "metrics": _average_metrics(per_query),
            "metrics_by_query_type": _metrics_by_type(per_query),
            "per_query": per_query,
        }

    @staticmethod
    def _query_metrics(query: GoldenQuery, results: list[Any]) -> dict[str, float]:
        metrics: dict[str, float] = {}
        for k in RECALL_K:
            metrics[f"physical_recall_at_{k}"] = physical_recall_at_k(
                results, query.relevant, k
            )
            metrics[f"logical_recall_at_{k}"] = logical_recall_at_k(
                results, query.relevant, k
            )
            metrics[f"physical_precision_at_{k}"] = physical_precision_at_k(
                results, query.relevant, k
            )
            metrics[f"logical_precision_at_{k}"] = logical_precision_at_k(
                results, query.relevant, k
            )
            metrics[f"physical_hit_rate_at_{k}"] = physical_hit_rate_at_k(
                results, query.relevant, k
            )
            metrics[f"logical_hit_rate_at_{k}"] = logical_hit_rate_at_k(
                results, query.relevant, k
            )
        for k in RANKING_K:
            metrics[f"physical_mrr_at_{k}"] = physical_mrr_at_k(
                results, query.relevant, k
            )
            metrics[f"logical_mrr_at_{k}"] = logical_mrr_at_k(
                results, query.relevant, k
            )
            metrics[f"physical_ndcg_at_{k}"] = physical_ndcg_at_k(
                results, query.relevant, k
            )
            metrics[f"logical_ndcg_at_{k}"] = logical_ndcg_at_k(
                results, query.relevant, k
            )
        return metrics


def write_evaluation_report(report: dict[str, Any], output_dir: str | Path) -> None:
    destination = Path(output_dir)
    destination.mkdir(parents=True, exist_ok=True)
    (destination / "metrics.json").write_text(
        json.dumps(
            {key: value for key, value in report.items() if key != "per_query"},
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    (destination / "per_query.json").write_text(
        json.dumps(report["per_query"], ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (destination / "report.md").write_text(_markdown_report(report), encoding="utf-8")


def _average_metrics(per_query: list[dict[str, Any]]) -> dict[str, float]:
    names = per_query[0]["metrics"]
    return {
        name: mean(item["metrics"][name] for item in per_query)
        for name in names
    }


def _metrics_by_type(per_query: list[dict[str, Any]]) -> dict[str, dict[str, float]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in per_query:
        groups[item["query_type"]].append(item)
    return {query_type: _average_metrics(items) for query_type, items in groups.items()}


def _markdown_report(report: dict[str, Any]) -> str:
    misses = [
        item
        for item in report["per_query"]
        if item["metrics"]["logical_recall_at_10"] == 0
    ]
    lines = [
        "# BM25 Retrieval Evaluation",
        "",
        f"- Dataset version: `{report['dataset_version']}`",
        f"- Dataset size: {report['dataset_size']}",
        f"- Elasticsearch index: `{report['index_name']}`",
        "- Index configuration: "
        f"`{json.dumps(report['index_configuration'], ensure_ascii=False)}`",
        f"- Run time (UTC): `{report['run_time']}`",
        f"- Query fields: `{', '.join(report['query_fields'])}`",
        f"- Physical candidate pool: {report['candidate_pool']}",
        "- Valid related targets: "
        f"{report.get('validation', {}).get('valid_targets', 'not recorded')}",
        "- Chunk dataset: "
        f"`{json.dumps(report.get('chunk_dataset', {}), ensure_ascii=False)}`",
        "- Golden Dataset fingerprint: "
        f"`{report.get('golden_dataset_fingerprint', 'not recorded')}`",
        f"- Elasticsearch version: `{report.get('elasticsearch_version', 'not recorded')}`",
        "",
        "## Overall metrics",
        "",
        "| Metric | Value |",
        "| --- | ---: |",
    ]
    lines.extend(f"| {name} | {value:.6f} |" for name, value in report["metrics"].items())
    insufficient = sum(
        item["logical_candidate_pool_insufficient"] for item in report["per_query"]
    )
    lines.extend(
        [
            "",
            "Physical metrics use the first K Elasticsearch hits; duplicate physical "
            "Chunks occupy rank positions. Logical metrics deduplicate the configured "
            "candidate pool before taking K.",
            f"Queries with fewer than {max(RECALL_K)} logical candidates: {insufficient}",
        ]
    )
    lines.extend(["", "## Metrics by query type", ""])
    for query_type, metrics in report["metrics_by_query_type"].items():
        lines.append(f"### {query_type}")
        lines.append("")
        lines.extend(f"- {name}: {value:.6f}" for name, value in metrics.items())
        lines.append("")
    lines.extend(["## Missed queries", ""])
    if misses:
        for item in misses:
            top_result = item["results"][0] if item["results"] else None
            top_summary = (
                f"top result `{top_result['document_id']} / "
                f"{top_result.get('clause_number') or top_result['chunk_id']}` "
                f"(score {top_result['score']:.6f})"
                if top_result
                else "no result returned"
            )
            lines.append(f"- `{item['query_id']}`: {item['query']} — {top_summary}")
    else:
        lines.append("No Recall@10 misses in this run.")
    lines.extend(
        [
            "",
            "## Typical failures and possible causes",
            "",
            "Inspect the ranked results in `per_query.json`. Common baseline causes include "
            "the built-in standard analyzer's limited Chinese term segmentation, vocabulary "
            "mismatch, missing or incorrect Chunk metadata, and incomplete human judgments.",
            "",
            "Future experiments should be evaluated against the same versioned judgments "
            "before adopting analyzer, query, or ranking changes.",
            "",
        ]
    )
    return "\n".join(lines)
