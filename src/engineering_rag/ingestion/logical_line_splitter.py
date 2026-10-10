"""Split PDF text blocks only at conservative document-structure boundaries."""

from __future__ import annotations

import re

from pydantic import BaseModel, ConfigDict, Field

from engineering_rag.ingestion.parser import TextBlock


class LogicalSegment(BaseModel):
    """A logical part of one source TextBlock.

    ``bbox`` intentionally remains the original block-level bounding box. PyMuPDF's
    block extraction does not provide a trustworthy box for these derived segments.
    """

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    page_number: int = Field(ge=1)
    source_block_number: int = Field(ge=0)
    segment_index: int = Field(ge=0)
    bbox: list[float] = Field(min_length=4, max_length=4)
    font_size: float | None = None
    font_name: str | None = None
    is_bold: bool = False


class LogicalLineSplitter:
    """Preserve ordinary lines while exposing clear structural line starts."""

    _BOUNDARIES = (
        re.compile(r"^(?:\d+|[A-Z])\.\d+\.\d+(?![.\w-])(?:\s+.*)?$"),
        re.compile(r"^\d+\.\d+(?![.\w-])\s+\S.*$"),
        re.compile(r"^第[一二三四五六七八九十百零〇0-9]+章(?:\s+.*)?$"),
        re.compile(r"^附录\s*[A-Z](?:\s+.*)?$"),
        re.compile(r"^[A-Z]\.\d+(?![.\w-])(?:\s+.*)?$"),
        re.compile(r"^注\s*\d*\s*[:：].*$"),
        re.compile(r"^(?:工程建设标准)?条文说明(?:\s*部分)?$"),
        re.compile(r"^(?:本规范用词说明|引用标准名录)$"),
    )

    def split(self, page_number: int, block: TextBlock) -> list[LogicalSegment]:
        """Return ordered segments without inventing line-level coordinates."""

        lines = [
            line.strip()
            for line in block.text.replace("\r\n", "\n")
            .replace("\r", "\n")
            .split("\n")
        ]
        lines = [line for line in lines if line]
        if not lines:
            return []

        groups: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            if self._is_boundary(line) and current:
                groups.append(current)
                current = []
            current.append(line)
        if current:
            groups.append(current)

        return [
            LogicalSegment(
                text="\n".join(group),
                page_number=page_number,
                source_block_number=block.block_number,
                segment_index=index,
                bbox=list(block.bbox),
                font_size=block.font_size,
                font_name=block.font_name,
                is_bold=block.is_bold,
            )
            for index, group in enumerate(groups)
        ]

    @classmethod
    def _is_boundary(cls, line: str) -> bool:
        return any(pattern.fullmatch(line) for pattern in cls._BOUNDARIES)
