"""Core data models used by the engineering RAG pipeline."""

from pydantic import BaseModel, ConfigDict, Field, model_validator


class Chunk(BaseModel):
    """A text chunk and its source metadata for retrieval and citation."""

    model_config = ConfigDict(extra="forbid")

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    content: str = Field(min_length=1)
    page_start: int = Field(ge=1)
    page_end: int = Field(ge=1)
    standard_name: str | None = None
    standard_code: str | None = None
    clause_number: str | None = None
    section_path: list[str] = Field(default_factory=list)
    content_type: str = Field(min_length=1)
    is_mandatory: bool = False
    is_explanation: bool = False

    @model_validator(mode="after")
    def validate_page_range(self) -> "Chunk":
        """Ensure the page range is ordered."""

        if self.page_end < self.page_start:
            raise ValueError("page_end must be greater than or equal to page_start")
        return self
