"""Parse text layers from digital PDF files with PyMuPDF."""

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
        blocks: list[TextBlock] = []
        for block in pdf_page.get_text("blocks", sort=True):
            text = block[4]
            if not text.strip():
                continue
            blocks.append(
                TextBlock(
                    text=text,
                    bbox=[block[0], block[1], block[2], block[3]],
                    block_number=block[5],
                    block_type=block[6],
                )
            )

        return Page(
            page_number=page_number,
            text=pdf_page.get_text("text", sort=True),
            blocks=blocks,
        )
