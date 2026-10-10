"""Validated schema for manually annotated retrieval datasets."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field, model_validator


class RelevanceTarget(BaseModel):
    """A stable logical source judged for one query."""

    model_config = ConfigDict(extra="forbid")

    document_id: str = Field(min_length=1)
    clause_number: str | None = None
    is_explanation: bool = False
    relevance: int = Field(ge=0, le=2)
    content_type: str | None = None
    logical_chunk_id: str | None = None
    source_block_ids: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_locator(self) -> "RelevanceTarget":
        if not self.clause_number and not self.logical_chunk_id and not self.source_block_ids:
            raise ValueError(
                "A target without clause_number requires logical_chunk_id or source_block_ids"
            )
        return self


class GoldenQuery(BaseModel):
    """One human-authored question and its relevance judgments."""

    model_config = ConfigDict(extra="forbid")

    query_id: str = Field(min_length=1)
    query: str = Field(min_length=1)
    query_type: str = Field(min_length=1)
    relevant: list[RelevanceTarget] = Field(min_length=1)

    @model_validator(mode="after")
    def require_positive_judgment(self) -> "GoldenQuery":
        if not any(target.relevance > 0 for target in self.relevant):
            raise ValueError("Each query requires at least one positive relevance judgment")
        return self


class GoldenDataset(BaseModel):
    """Versioned set of human relevance judgments."""

    model_config = ConfigDict(extra="forbid")

    version: str = Field(min_length=1)
    description: str | None = None
    queries: list[GoldenQuery] = Field(min_length=1)

    @model_validator(mode="after")
    def query_ids_are_unique(self) -> "GoldenDataset":
        query_ids = [query.query_id for query in self.queries]
        if len(query_ids) != len(set(query_ids)):
            raise ValueError("query_id values must be unique")
        return self


def load_golden_dataset(path: str | Path) -> GoldenDataset:
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Golden Dataset does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid Golden Dataset JSON in '{source}': {exc}") from exc
    return GoldenDataset.model_validate(payload)


def golden_dataset_fingerprint(dataset: GoldenDataset) -> str:
    """Return a deterministic hash of all dataset metadata and judgments."""

    payload = json.dumps(
        dataset.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()
