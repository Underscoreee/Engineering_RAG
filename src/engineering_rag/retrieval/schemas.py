"""Data contracts for indexing and keyword retrieval."""

from pydantic import BaseModel, ConfigDict, Field


class IndexingError(BaseModel):
    """One failed bulk indexing action."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    status: int | None = None
    reason: str


class IndexingResult(BaseModel):
    """Observable outcome of a bulk indexing operation."""

    model_config = ConfigDict(extra="forbid")

    success_count: int = Field(ge=0)
    failure_count: int = Field(ge=0)
    errors: list[IndexingError] = Field(default_factory=list)


class RetrievalResult(BaseModel):
    """A ranked Chunk returned by Elasticsearch."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str
    document_id: str
    content: str
    score: float
    rank: int = Field(ge=1)
    standard_name: str | None = None
    standard_code: str | None = None
    clause_number: str | None = None
    section_path: list[str] = Field(default_factory=list)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    content_type: str
    is_mandatory: bool = False
    is_explanation: bool = False
    source_block_ids: list[str] = Field(default_factory=list)
    context_header: str = ""
    logical_chunk_id: str | None = None
    parent_chunk_id: str | None = None
    chapter: str | None = None
    section: str | None = None
    table_id: str | None = None
    figure_id: str | None = None
    formula_id: str | None = None
