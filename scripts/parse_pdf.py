#!/usr/bin/env python3
"""Parse a digital PDF and print its document representation as JSON."""

import argparse
import sys
from pathlib import Path

# Allow direct execution from a source checkout without an editable install.
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engineering_rag.ingestion.parser import PdfParseError, PdfParser  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract text from a digital PDF as JSON.")
    parser.add_argument("pdf_path", help="Path to the input PDF")
    parser.add_argument("--output", help="Write JSON to this file instead of stdout")
    args = parser.parse_args()

    try:
        document = PdfParser().parse(args.pdf_path)
        output = document.model_dump_json(indent=2)
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
    except (OSError, ValueError, PdfParseError) as exc:
        print(f"parse_pdf: {exc}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
