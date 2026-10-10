"""BM25 keyword retrieval using structured Elasticsearch queries."""

from __future__ import annotations

from typing import Any, Mapping

from engineering_rag.retrieval.schemas import RetrievalResult


DEFAULT_FIELD_WEIGHTS: dict[str, float] = {
    "content": 3.0,
    "standard_name": 2.0,
    "standard_code": 2.0,
    "context_header": 1.0,
}

ALLOWED_FILTERS = frozenset(
    {"standard_code", "clause_number", "document_id", "content_type", "is_explanation"}
)


class BM25Retriever:
    """Retrieve ranked Chunk records with Elasticsearch native BM25 scoring."""

    def __init__(
        self,
        client: Any,
        index_name: str,
        *,
        field_weights: Mapping[str, float] | None = None,
    ) -> None:
        if not index_name:
            raise ValueError("index_name must not be empty")
        weights = dict(field_weights or DEFAULT_FIELD_WEIGHTS)
        if not weights or any(not field or weight <= 0 for field, weight in weights.items()):
            raise ValueError("field_weights must contain positive weights")
        self.client = client
        self.index_name = index_name
        self.field_weights = weights

    @property
    def query_fields(self) -> list[str]:
        return [f"{field}^{weight:g}" for field, weight in self.field_weights.items()]

    def build_query(
        self, query: str, filters: Mapping[str, Any] | None = None
    ) -> dict[str, Any]:
        text = query.strip()
        if not text:
            raise ValueError("query must not be empty")

        filter_clauses: list[dict[str, Any]] = []
        for field, value in (filters or {}).items():
            if field not in ALLOWED_FILTERS:
                raise ValueError(f"Unsupported BM25 filter: {field}")
            if value is None or value == "" or value == []:
                raise ValueError(f"Filter '{field}' must not be empty")
            filter_clauses.append(
                {"terms": {field: list(value)}}
                if isinstance(value, (list, tuple, set, frozenset))
                else {"term": {field: value}}
            )

        return {
            "bool": {
                "must": [
                    {
                        "multi_match": {
                            "query": text,
                            "fields": self.query_fields,
                            "type": "best_fields",
                        }
                    }
                ],
                "filter": filter_clauses,
            }
        }

    def search(
        self,
        query: str,
        top_k: int = 5,
        filters: Mapping[str, Any] | None = None,
    ) -> list[RetrievalResult]:
        if top_k < 1:
            raise ValueError("top_k must be at least 1")
        response = self.client.search(
            index=self.index_name,
            query=self.build_query(query, filters),
            size=top_k,
        )
        hits = sorted(
            response.get("hits", {}).get("hits", []),
            key=lambda hit: float(hit.get("_score") or 0.0),
            reverse=True,
        )
        results: list[RetrievalResult] = []
        for rank, hit in enumerate(hits, start=1):
            source = dict(hit.get("_source", {}))
            source["chunk_id"] = source.get("chunk_id") or hit.get("_id")
            results.append(
                RetrievalResult(
                    **{
                        key: value
                        for key, value in source.items()
                        if key in RetrievalResult.model_fields
                    },
                    score=float(hit.get("_score") or 0.0),
                    rank=rank,
                )
            )
        return results
