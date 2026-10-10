#!/usr/bin/env python3
"""Inspect a real digital PDF through the existing engineering RAG pipeline."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engineering_rag.ingestion.parser import PdfParseError  # noqa: E402
from engineering_rag.inspection import (  # noqa: E402
    inspect_pdf,
    render_terminal_report,
    write_before_after_structure_report,
    write_inspection_output,
)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Inspect a real PDF with the full local pipeline."
    )
    parser.add_argument("pdf_path", help="Path to the input PDF")
    parser.add_argument("--standard-name", help="Optional engineering standard name")
    parser.add_argument("--standard-code", help="Optional engineering standard code")
    parser.add_argument(
        "--max-tokens", type=int, help="Maximum estimated content tokens per chunk"
    )
    parser.add_argument(
        "--output-dir", default="data/debug", help="Directory for inspection artifacts"
    )
    parser.add_argument(
        "--max-chunks", type=int, default=20, help="Maximum chunks displayed in terminal"
    )
    parser.add_argument(
        "--content-chars",
        type=int,
        default=500,
        help="Maximum content characters displayed per chunk",
    )
    parser.add_argument(
        "--compare-with",
        help="Optional prior summary.json used to write before_after_structure_report.md",
    )
    args = parser.parse_args()

    if args.max_tokens is not None and args.max_tokens < 1:
        parser.error("--max-tokens must be at least 1")
    if args.max_chunks < 0:
        parser.error("--max-chunks cannot be negative")
    if args.content_chars < 0:
        parser.error("--content-chars cannot be negative")

    try:
        result = inspect_pdf(
            args.pdf_path,
            standard_name=args.standard_name,
            standard_code=args.standard_code,
            max_tokens=args.max_tokens,
        )
        write_inspection_output(result, args.output_dir)
        if args.compare_with:
            write_before_after_structure_report(
                result, args.compare_with, args.output_dir
            )
        print(
            render_terminal_report(
                result,
                max_chunks=args.max_chunks,
                content_chars=args.content_chars,
            ),
            end="",
        )
    except FileNotFoundError:
        print("ERROR: PDF file does not exist", file=sys.stderr)
        return 1
    except (OSError, ValueError, PdfParseError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
