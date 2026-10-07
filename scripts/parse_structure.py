#!/usr/bin/env python3
"""Parse a digital PDF and print recognized document structure as JSON."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engineering_rag.ingestion.parser import PdfParseError, PdfParser  # noqa: E402
from engineering_rag.ingestion.structure import StructureParser  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Recognize structure in a digital PDF.")
    parser.add_argument("pdf_path", help="Path to the input PDF")
    args = parser.parse_args()
    try:
        document = PdfParser().parse(args.pdf_path)
        structure = StructureParser().parse(document)
        print(structure.model_dump_json(indent=2))
    except (OSError, ValueError, PdfParseError) as exc:
        print(f"parse_structure: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
