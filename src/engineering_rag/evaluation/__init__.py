"""Golden dataset loading and retrieval evaluation."""

from engineering_rag.evaluation.dataset import (
    GoldenDataset,
    GoldenQuery,
    RelevanceTarget,
    load_golden_dataset,
)
from engineering_rag.evaluation.evaluator import RetrievalEvaluator
from engineering_rag.evaluation.metrics import (
    hit_rate_at_k,
    logical_hit_rate_at_k,
    logical_mrr_at_k,
    logical_ndcg_at_k,
    logical_precision_at_k,
    logical_recall_at_k,
    mrr_at_k,
    ndcg_at_k,
    physical_hit_rate_at_k,
    physical_mrr_at_k,
    physical_ndcg_at_k,
    physical_precision_at_k,
    physical_recall_at_k,
    precision_at_k,
    recall_at_k,
)
from engineering_rag.evaluation.validator import (
    GoldenDatasetValidator,
    ValidationReport,
    ValidationStatus,
)

__all__ = [
    "GoldenDataset",
    "GoldenQuery",
    "GoldenDatasetValidator",
    "RelevanceTarget",
    "RetrievalEvaluator",
    "ValidationReport",
    "ValidationStatus",
    "hit_rate_at_k",
    "logical_hit_rate_at_k",
    "logical_mrr_at_k",
    "logical_ndcg_at_k",
    "logical_precision_at_k",
    "logical_recall_at_k",
    "load_golden_dataset",
    "mrr_at_k",
    "ndcg_at_k",
    "physical_hit_rate_at_k",
    "physical_mrr_at_k",
    "physical_ndcg_at_k",
    "physical_precision_at_k",
    "physical_recall_at_k",
    "precision_at_k",
    "recall_at_k",
]
