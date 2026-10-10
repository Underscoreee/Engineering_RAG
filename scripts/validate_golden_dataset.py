#!/usr/bin/env python3
"""Validate a Golden Dataset against a generated chunks.json file."""

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engineering_rag.evaluation import (  # noqa: E402
    GoldenDatasetValidator,
    load_golden_dataset,
)
from engineering_rag.evaluation.validator import write_validation_report  # noqa: E402
from engineering_rag.retrieval.indexer import load_chunks  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--chunks", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args()
    try:
        dataset = load_golden_dataset(args.dataset)
        chunks = load_chunks(args.chunks)
        report = GoldenDatasetValidator().validate(dataset, chunks)
        write_validation_report(report, args.output_dir)
    except Exception as exc:
        print(f"Golden Dataset validation failed: {exc}", file=sys.stderr)
        return 1
    print(report.model_dump_json(indent=2))
    return 0 if report.is_valid else 2


if __name__ == "__main__":
    raise SystemExit(main())
