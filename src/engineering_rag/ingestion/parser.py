"""Parse text layers from digital PDF files with PyMuPDF."""

from collections import Counter
from pathlib import Path

import pymupdf
from pydantic import BaseModel, ConfigDict, Field


class TextBlock(BaseModel):
    """A text block in PDF page coordinates."""

    model_config = ConfigDict(extra="forbid")

    text: str
    bbox: list[float] = Field(min_length=4, max_length=4)
    block_number: int
    block_type: int
    font_size: float | None = None
    font_name: str | None = None
    is_bold: bool = False


class Page(BaseModel):
    """Extracted text and blocks for a one-based PDF page number."""

    model_config = ConfigDict(extra="forbid")

    page_number: int = Field(ge=1)
    text: str
    blocks: list[TextBlock] = Field(default_factory=list)


class Document(BaseModel):
    """Parsed PDF and its pages."""

    model_config = ConfigDict(extra="forbid")

    document_id: str
    source_file: str
    page_count: int = Field(ge=0)
    pages: list[Page] = Field(default_factory=list)


class PdfParseError(Exception):
    """Raised when a PDF exists but cannot be parsed."""


class PdfParser:
    """Extract page text and text blocks from a digital PDF."""

    def parse(self, pdf_path: str | Path) -> Document:
        """Parse ``pdf_path`` and return a JSON-serializable Document."""

        path = Path(pdf_path)
        if not path.is_file():
            raise FileNotFoundError(f"PDF file does not exist: {path}")

        try:
            pdf_document = pymupdf.open(path)
        except Exception as exc:
            raise PdfParseError(f"Unable to open PDF '{path}': {exc}") from exc

        try:
            pages = [self._parse_page(page, index + 1) for index, page in enumerate(pdf_document)]
        except Exception as exc:
            raise PdfParseError(f"Unable to parse PDF '{path}': {exc}") from exc
        finally:
            pdf_document.close()

        return Document(
            document_id=path.stem,
            source_file=str(path),
            page_count=len(pages),
            pages=pages,
        )

    @staticmethod
    def _parse_page(pdf_page: pymupdf.Page, page_number: int) -> Page:
        style_by_number = PdfParser._extract_block_styles(pdf_page)
        blocks: list[TextBlock] = []
        for block in pdf_page.get_text("blocks", sort=True):
            text = block[4]
            if not text.strip():
                continue
            font_size, font_name, is_bold = style_by_number.get(block[5], (None, None, False))
            blocks.append(
                TextBlock(
                    text=text,
                    bbox=[block[0], block[1], block[2], block[3]],
                    block_number=block[5],
                    block_type=block[6],
                    font_size=font_size,
                    font_name=font_name,
                    is_bold=is_bold,
                )
            )

        return Page(
            page_number=page_number,
            text=pdf_page.get_text("text", sort=True),
            blocks=blocks,
        )

    @staticmethod
    def _extract_block_styles(
        pdf_page: pymupdf.Page,
    ) -> dict[int, tuple[float | None, str | None, bool]]:
        """Select the character-dominant span style for each text block."""

        styles: dict[int, tuple[float | None, str | None, bool]] = {}
        page_dict = pdf_page.get_text("dict", sort=True)
        for raw_block in page_dict["blocks"]:
            if raw_block.get("type") != 0:
                continue
            spans = [
                span
                for line in raw_block.get("lines", [])
                for span in line.get("spans", [])
                if span.get("text", "").strip()
            ]
            if not spans:
                continue

            def style_key(span: dict) -> tuple[float, str, bool]:
                font_name = str(span.get("font", "")) or None
                flags = int(span.get("flags", 0))
                is_bold = bool(flags & pymupdf.TEXT_FONT_BOLD) or bool(
                    font_name and any(part in font_name.lower() for part in ("bold", "black", "demi"))
                )
                return float(span["size"]), font_name or "", is_bold

            weights = Counter()
            for span in spans:
                weights[style_key(span)] += len(span.get("text", "").strip())
            (font_size, font_name, is_bold), _ = max(
                weights.items(), key=lambda item: (item[1], item[0][0])
            )
            styles[int(raw_block["number"])] = (
                font_size,
                font_name or None,
                is_bold,
            )
        return styles
