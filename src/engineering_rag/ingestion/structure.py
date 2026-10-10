"""Rule-based recognition of engineering-standard document structure."""

import re
from collections import Counter, defaultdict
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

from engineering_rag.ingestion.logical_line_splitter import (
    LogicalLineSplitter,
    LogicalSegment,
)
from engineering_rag.ingestion.parser import Document, TextBlock


class StructureRole(str, Enum):
    """Recognized roles for text blocks in a standard document."""

    DOCUMENT_TITLE = "document_title"
    CHAPTER = "chapter"
    SECTION = "section"
    CLAUSE = "clause"
    PARAGRAPH = "paragraph"
    NOTE = "note"
    APPENDIX = "appendix"
    APPENDIX_SECTION = "appendix_section"
    EXPLANATION_HEADING = "explanation_heading"
    HEADER = "header"
    FOOTER = "footer"
    UNKNOWN = "unknown"


class StructuredBlock(BaseModel):
    """A source text block annotated with its document structure."""

    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    text: str
    bbox: list[float] = Field(min_length=4, max_length=4)
    role: StructureRole
    chapter: str | None = None
    section: str | None = None
    clause_number: str | None = None
    section_path: list[str] = Field(default_factory=list)
    is_explanation: bool = False
    font_size: float | None = None
    is_bold: bool = False
    source_block_number: int
    segment_index: int = Field(default=0, ge=0)


class DocumentStructure(BaseModel):
    """Structured blocks in document reading order."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    source_file: str | None = None
    standard_name: str | None = None
    standard_code: str | None = None
    blocks: list[StructuredBlock] = Field(default_factory=list)


class StructureParser:
    """Recognize common chapter, section, clause, and note patterns."""

    _CHINESE_CHAPTER = re.compile(
        r"^(第[一二三四五六七八九十百零〇0-9]+章)(?:\s+[\s\S]*)?$"
    )
    _NUMBERED_CHAPTER = re.compile(r"^(\d+)\s+\S[\s\S]*$")
    _SECTION = re.compile(r"^(\d+\.\d+)(?![.\w-])\s+\S[\s\S]*$")
    _CLAUSE = re.compile(
        r"^((?:\d+|[A-Z])\.\d+\.\d+)(?![.\w-])(?:\s+[\s\S]*)?$"
    )
    _APPENDIX = re.compile(r"^附录\s*([A-Z])(?:\s+[\s\S]*)?$")
    _APPENDIX_SECTION = re.compile(
        r"^([A-Z])\.(\d+)(?![.\w-])(?:\s+[\s\S]*)?$"
    )
    _NOTE = re.compile(r"^注\s*\d*\s*[:：][\s\S]*$")
    _UNRECOGNIZED_NUMBER = re.compile(r"^\d+(?:\.\d+){2,}[\w.-]*\b[\s\S]*$")

    def __init__(self, logical_line_splitter: LogicalLineSplitter | None = None) -> None:
        self.logical_line_splitter = logical_line_splitter or LogicalLineSplitter()

    def parse(self, document: Document) -> DocumentStructure:
        """Return structural annotations without altering the source document."""

        state = _StructureState()
        source_blocks = [
            (page.page_number, block)
            for page in document.pages
            for block in page.blocks
        ]
        repeated_margin_roles = self._find_repeated_margin_blocks(source_blocks)
        structured: list[StructuredBlock] = []

        for page_number, block in source_blocks:
            margin_role = repeated_margin_roles.get((page_number, block.block_number))
            segments = self.logical_line_splitter.split(page_number, block)
            for segment in segments:
                if margin_role is not None:
                    structured.append(self._make_margin_block(segment, margin_role, state))
                    continue
                structured.append(self._classify(segment, state))

        return DocumentStructure(
            document_id=document.document_id,
            source_file=document.source_file,
            standard_name=document.standard_name,
            standard_code=document.standard_code,
            blocks=structured,
        )

    def _classify(
        self, segment: LogicalSegment, state: "_StructureState"
    ) -> StructuredBlock:
        text = segment.text.strip()
        role = StructureRole.PARAGRAPH

        state.explanation_mode = self._transition_explanation_mode(
            text, state.explanation_mode
        )

        if self._is_explanation_heading(text):
            role = StructureRole.EXPLANATION_HEADING
        elif self._is_explanation_exit_heading(text):
            role = StructureRole.CHAPTER
            state.current_chapter = text
            state.current_section = None
            state.current_clause = None
        elif (match := self._APPENDIX.match(text)) and self._has_heading_style(segment):
            role = StructureRole.APPENDIX
            state.current_chapter = f"附录 {match.group(1)}"
            state.current_section = None
            state.current_clause = None
        elif self._CHINESE_CHAPTER.match(text):
            role = StructureRole.CHAPTER
            state.current_chapter = text
            state.current_section = None
            state.current_clause = None
        elif self._NUMBERED_CHAPTER.match(text) and self._is_numbered_chapter(
            segment
        ):
            role = StructureRole.CHAPTER
            state.current_chapter = text
            state.current_section = None
            state.current_clause = None
        elif match := self._APPENDIX_SECTION.match(text):
            role = StructureRole.APPENDIX_SECTION
            state.current_section = text
            state.current_clause = None
        elif match := self._SECTION.match(text):
            role = StructureRole.SECTION
            state.current_section = text
            state.current_clause = None
        elif match := self._CLAUSE.match(text):
            role = StructureRole.CLAUSE
            state.current_clause = match.group(1)
        elif self._NOTE.match(text):
            role = StructureRole.NOTE
        elif self._UNRECOGNIZED_NUMBER.match(text):
            role = StructureRole.UNKNOWN
        elif state.is_first_block and segment.is_bold and (segment.font_size or 0) >= 18:
            role = StructureRole.DOCUMENT_TITLE

        is_explanation = state.explanation_mode
        if role == StructureRole.EXPLANATION_HEADING:
            is_explanation = True
        state.is_first_block = False

        path = state.section_path
        return StructuredBlock(
            page_number=segment.page_number,
            text=segment.text,
            bbox=segment.bbox,
            role=role,
            chapter=state.current_chapter,
            section=state.current_section,
            clause_number=state.current_clause,
            section_path=path,
            is_explanation=is_explanation,
            font_size=segment.font_size,
            is_bold=segment.is_bold,
            source_block_number=segment.source_block_number,
            segment_index=segment.segment_index,
        )

    @staticmethod
    def _transition_explanation_mode(text: str, current: bool) -> bool:
        """Change mode only at exact, semantic document boundaries."""

        if StructureParser._is_explanation_heading(text):
            return True
        if StructureParser._is_explanation_exit_heading(text):
            return False
        return current

    @staticmethod
    def _is_explanation_exit_heading(text: str) -> bool:
        return text in {"本规范用词说明", "引用标准名录"}

    @staticmethod
    def _has_heading_style(segment: LogicalSegment) -> bool:
        """Keep synthetic inputs usable while rejecting small-font numbered lists."""

        return segment.font_size is None or segment.font_size >= 13

    @staticmethod
    def _is_numbered_chapter(segment: LogicalSegment) -> bool:
        if StructureParser._has_heading_style(segment):
            return True
        title = re.sub(r"^\d+\s+", "", segment.text.strip()).replace("\n", "")
        return bool(
            len(title) <= 30
            and re.search(
                r"(?:总则|术语和符号|规定|材料|分析|计算|验算|设计)$",
                title,
            )
        )

    @staticmethod
    def _make_margin_block(
        segment: LogicalSegment,
        role: StructureRole,
        state: "_StructureState",
    ) -> StructuredBlock:
        """Represent a repeated margin without mutating structural state."""

        return StructuredBlock(
            page_number=segment.page_number,
            text=segment.text,
            bbox=segment.bbox,
            role=role,
            chapter=state.current_chapter,
            section=state.current_section,
            clause_number=state.current_clause,
            section_path=state.section_path,
            is_explanation=state.explanation_mode,
            font_size=segment.font_size,
            is_bold=segment.is_bold,
            source_block_number=segment.source_block_number,
            segment_index=segment.segment_index,
        )

    @staticmethod
    def _is_explanation_heading(text: str) -> bool:
        return bool(re.fullmatch(r"(?:工程建设标准)?条文说明(?:\s*部分)?", text))

    @staticmethod
    def _find_repeated_margin_blocks(
        source_blocks: list[tuple[int, TextBlock]],
    ) -> dict[tuple[int, int], StructureRole]:
        """Mark only identical text repeated at conservative page margins."""

        candidates: dict[tuple[str, StructureRole], list[tuple[int, TextBlock]]] = defaultdict(list)
        for page_number, block in source_blocks:
            y0, y1 = block.bbox[1], block.bbox[3]
            margin_role = (
                StructureRole.HEADER
                if y0 <= 36
                else StructureRole.FOOTER
                if y0 >= 760 and y1 >= 760
                else None
            )
            if margin_role is not None and block.text.strip():
                candidates[(block.text.strip(), margin_role)].append((page_number, block))

        marked: dict[tuple[int, int], StructureRole] = {}
        for (_, role), occurrences in candidates.items():
            pages = {page_number for page_number, _ in occurrences}
            if len(pages) >= 2:
                for page_number, block in occurrences:
                    marked[(page_number, block.block_number)] = role
        return marked


class _StructureState:
    def __init__(self) -> None:
        self.current_chapter: str | None = None
        self.current_section: str | None = None
        self.current_clause: str | None = None
        self.explanation_mode = False
        self.is_first_block = True

    @property
    def section_path(self) -> list[str]:
        return [
            value
            for value in (self.current_chapter, self.current_section, self.current_clause)
            if value is not None
        ]
