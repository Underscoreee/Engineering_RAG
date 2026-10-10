"""Verify that an Elasticsearch index represents one exact Chunk dataset."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from engineering_rag.models import Chunk
from engineering_rag.retrieval.indexer import (
    CHUNK_MAPPING_VERSION,
    chunk_dataset_fingerprint,
)


class IndexDatasetValidation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    index_name: str
    expected_chunk_count: int = Field(ge=0)
    actual_chunk_count: int = Field(ge=0)
    expected_fingerprint: str
    recorded_fingerprint: str | None = None
    expected_mapping_version: str
    recorded_mapping_version: str | None = None
    is_valid: bool
    errors: list[str] = Field(default_factory=list)


def validate_index_dataset(
    client: Any, index_name: str, chunks: list[Chunk]
) -> IndexDatasetValidation:
    expected_count = len(chunks)
    expected_fingerprint = chunk_dataset_fingerprint(chunks)
    actual_count = int(client.count(index=index_name)["count"])
    response = client.indices.get_mapping(index=index_name)
    metadata = response.get(index_name, {}).get("mappings", {}).get("_meta", {})
    recorded_fingerprint = metadata.get("chunk_fingerprint")
    recorded_mapping_version = metadata.get("mapping_version")
    recorded_count = metadata.get("chunk_count")
    errors: list[str] = []
    if actual_count != expected_count:
        errors.append(
            f"Index count {actual_count} does not match Chunk count {expected_count}."
        )
    if recorded_count != str(expected_count):
        errors.append("Recorded Chunk count is missing or does not match.")
    if recorded_fingerprint != expected_fingerprint:
        errors.append("Recorded Chunk dataset fingerprint is missing or does not match.")
    if recorded_mapping_version != CHUNK_MAPPING_VERSION:
        errors.append("Recorded mapping version is missing or does not match.")
    return IndexDatasetValidation(
        index_name=index_name,
        expected_chunk_count=expected_count,
        actual_chunk_count=actual_count,
        expected_fingerprint=expected_fingerprint,
        recorded_fingerprint=recorded_fingerprint,
        expected_mapping_version=CHUNK_MAPPING_VERSION,
        recorded_mapping_version=recorded_mapping_version,
        is_valid=not errors,
        errors=errors,
    )
