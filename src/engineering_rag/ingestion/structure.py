"""Rule-based recognition of engineering-standard document structure."""

import re
from collections import Counter, defaultdict
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field

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


class DocumentStructure(BaseModel):
    """Structured blocks in document reading order."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    blocks: list[StructuredBlock] = Field(default_factory=list)
    standard_name: str | None = None
    standard_code: str | None = None


class StructureParser:
    """Recognize common chapter, section, clause, and note patterns."""

    _CHINESE_CHAPTER = re.compile(r"^(第[一二三四五六七八九十百零〇0-9]+章)\s*(.*)$")
    _NUMBERED_CHAPTER = re.compile(r"^(\d+)\s+\S.*$")
    _SECTION = re.compile(r"^(\d+\.\d+)(?![.\w-])(?:\s+.*)?$")
    _CLAUSE = re.compile(r"^(\d+\.\d+\.\d+)(?![.\w-])(?:\s+.*)?$")
    _APPENDIX = re.compile(r"^附录\s*([A-Z])(?:\s+.*)?$")
    _APPENDIX_SECTION = re.compile(r"^([A-Z])\.(\d+)(?![.\w-])(?:\s+.*)?$")
    _NOTE = re.compile(r"^注\s*\d*\s*[:：].*$")
    _UNRECOGNIZED_NUMBER = re.compile(r"^\d+(?:\.\d+){2,}[\w.-]*\b.*$")

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
            item = self._classify(page_number, block, state)
            margin_role = repeated_margin_roles.get((page_number, block.block_number))
            if margin_role is not None and item.role in (StructureRole.PARAGRAPH, StructureRole.UNKNOWN):
                item.role = margin_role
            structured.append(item)

        return DocumentStructure(document_id=document.document_id, blocks=structured)

    def _classify(self, page_number: int, block: TextBlock, state: "_StructureState") -> StructuredBlock:
        text = block.text.strip()
        role = StructureRole.PARAGRAPH

        if self._is_explanation_heading(text):
            role = StructureRole.EXPLANATION_HEADING
            state.explanation_mode = True
        elif match := self._APPENDIX.match(text):
            role = StructureRole.APPENDIX
            state.explanation_mode = False
            state.current_chapter = f"附录 {match.group(1)}"
            state.current_section = None
            state.current_clause = None
        elif match := self._CHINESE_CHAPTER.match(text):
            role = StructureRole.CHAPTER
            state.explanation_mode = False
            state.current_chapter = text
            state.current_section = None
            state.current_clause = None
        elif match := self._NUMBERED_CHAPTER.match(text):
            role = StructureRole.CHAPTER
            state.explanation_mode = False
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
        elif state.is_first_block and block.is_bold and (block.font_size or 0) >= 18:
            role = StructureRole.DOCUMENT_TITLE

        is_explanation = state.explanation_mode
        if role == StructureRole.EXPLANATION_HEADING:
            is_explanation = True
        state.is_first_block = False

        path = state.section_path
        return StructuredBlock(
            page_number=page_number,
            text=block.text,
            bbox=block.bbox,
            role=role,
            chapter=state.current_chapter,
            section=state.current_section,
            clause_number=state.current_clause,
            section_path=path,
            is_explanation=is_explanation,
            font_size=block.font_size,
            is_bold=block.is_bold,
            source_block_number=block.block_number,
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
