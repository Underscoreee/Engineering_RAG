"""Create the Chunk index and write Chunk records with the Bulk API."""

from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Iterable

from pydantic import TypeAdapter

from engineering_rag.models import Chunk
from engineering_rag.retrieval.schemas import IndexingError, IndexingResult


CHUNK_INDEX_SETTINGS: dict[str, Any] = {
    "number_of_shards": 1,
    "number_of_replicas": 0,
    "analysis": {"analyzer": {"engineering_standard": {"type": "standard"}}},
}

CHUNK_INDEX_MAPPING: dict[str, Any] = {
    "dynamic": "strict",
    "_meta": {"mapping_version": "engineering_rag_chunks_v1"},
    "properties": {
        "chunk_id": {"type": "keyword"},
        "logical_chunk_id": {"type": "keyword"},
        "document_id": {"type": "keyword"},
        "content": {"type": "text", "analyzer": "engineering_standard"},
        "embedding_text": {"type": "text", "analyzer": "engineering_standard"},
        "context_header": {"type": "text", "analyzer": "engineering_standard"},
        "standard_name": {
            "type": "text",
            "analyzer": "engineering_standard",
            "fields": {"keyword": {"type": "keyword"}},
        },
        "standard_code": {"type": "keyword"},
        "clause_number": {"type": "keyword"},
        "section_path": {"type": "keyword"},
        "content_type": {"type": "keyword"},
        "is_mandatory": {"type": "boolean"},
        "is_explanation": {"type": "boolean"},
        "page_start": {"type": "integer"},
        "page_end": {"type": "integer"},
        "source_block_ids": {"type": "keyword"},
        "token_count": {"type": "integer"},
        "parent_chunk_id": {"type": "keyword"},
        "chapter": {"type": "keyword"},
        "section": {"type": "keyword"},
        "table_id": {"type": "keyword"},
        "figure_id": {"type": "keyword"},
        "formula_id": {"type": "keyword"},
    },
}
CHUNK_MAPPING_VERSION = "engineering_rag_chunks_v1"


class ElasticsearchChunkIndexer:
    """Manage one explicit Elasticsearch index of Chunk documents."""

    def __init__(
        self,
        client: Any,
        index_name: str,
        *,
        refresh: bool = False,
        batch_size: int = 500,
    ) -> None:
        if not index_name:
            raise ValueError("index_name must not be empty")
        if batch_size < 1:
            raise ValueError("batch_size must be at least 1")
        self.client = client
        self.index_name = index_name
        self.refresh = refresh
        self.batch_size = batch_size

    def create_index(self, recreate: bool = False) -> None:
        exists = bool(self.client.indices.exists(index=self.index_name))
        if exists and not recreate:
            return
        if exists:
            self.client.indices.delete(index=self.index_name)
        self.client.indices.create(
            index=self.index_name,
            settings=CHUNK_INDEX_SETTINGS,
            mappings=CHUNK_INDEX_MAPPING,
        )

    def index_chunks(
        self, chunks: list[Chunk], *, record_dataset_metadata: bool = False
    ) -> IndexingResult:
        if not chunks:
            return IndexingResult(success_count=0, failure_count=0)

        success_count = 0
        errors: list[IndexingError] = []
        for batch in _batched(chunks, self.batch_size):
            operations: list[dict[str, Any]] = []
            for chunk in batch:
                operations.append(
                    {"index": {"_index": self.index_name, "_id": chunk.chunk_id}}
                )
                operations.append(chunk.model_dump(mode="json"))

            response = self.client.bulk(
                operations=operations,
                refresh=self.refresh,
            )
            items = response.get("items", [])
            if len(items) != len(batch):
                raise RuntimeError(
                    "Elasticsearch Bulk API returned an unexpected number of item results"
                )
            for chunk, item in zip(batch, items, strict=True):
                outcome = item.get("index", {})
                status = outcome.get("status")
                if isinstance(status, int) and 200 <= status < 300 and not outcome.get("error"):
                    success_count += 1
                    continue
                error = outcome.get("error", "unknown bulk indexing error")
                reason = (
                    error.get("reason", json.dumps(error, ensure_ascii=False))
                    if isinstance(error, dict)
                    else str(error)
                )
                errors.append(
                    IndexingError(chunk_id=chunk.chunk_id, status=status, reason=reason)
                )

        result = IndexingResult(
            success_count=success_count,
            failure_count=len(errors),
            errors=errors,
        )
        if record_dataset_metadata and not errors:
            self.record_dataset_metadata(chunks)
        return result

    def record_dataset_metadata(self, chunks: list[Chunk]) -> None:
        """Verify a full replacement dataset and store reproducibility metadata."""

        self.client.indices.refresh(index=self.index_name)
        actual_count = int(self.client.count(index=self.index_name)["count"])
        if actual_count != len(chunks):
            raise RuntimeError(
                "Index document count does not match the complete Chunk dataset: "
                f"index={actual_count}, chunks={len(chunks)}"
            )
        self.client.indices.put_mapping(
            index=self.index_name,
            meta={
                "mapping_version": CHUNK_MAPPING_VERSION,
                "chunk_count": str(len(chunks)),
                "chunk_fingerprint": chunk_dataset_fingerprint(chunks),
            },
        )


def load_chunks(path: str | Path) -> list[Chunk]:
    """Load the Chunk array emitted by Task 4.2."""

    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"Chunk JSON file does not exist: {source}")
    try:
        payload = json.loads(source.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid Chunk JSON in '{source}': {exc}") from exc
    return TypeAdapter(list[Chunk]).validate_python(payload)


def chunk_dataset_fingerprint(chunks: list[Chunk]) -> str:
    """Hash complete canonical Chunk records independently of input ordering."""

    canonical = [
        chunk.model_dump(mode="json")
        for chunk in sorted(chunks, key=lambda item: item.chunk_id)
    ]
    payload = json.dumps(
        canonical,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _batched(items: list[Chunk], size: int) -> Iterable[list[Chunk]]:
    for start in range(0, len(items), size):
        yield items[start : start + size]
