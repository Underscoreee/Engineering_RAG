#!/usr/bin/env python3
"""Convert a serialized DocumentStructure into chunk JSON."""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from engineering_rag.chunking import EngineeringChunker  # noqa: E402
from engineering_rag.ingestion.structure import DocumentStructure  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Chunk a serialized document structure.")
    parser.add_argument("input", help="Path to a DocumentStructure JSON file")
    parser.add_argument("--output", help="Write chunk JSON to this file instead of stdout")
    parser.add_argument("--max-tokens", type=int, default=800, help="Maximum estimated content tokens per chunk")
    args = parser.parse_args()

    try:
        structure = DocumentStructure.model_validate_json(
            Path(args.input).read_text(encoding="utf-8")
        )
        chunks = EngineeringChunker(max_tokens=args.max_tokens).chunk(structure)
        output = json.dumps(
            [chunk.model_dump(mode="json") for chunk in chunks],
            ensure_ascii=False,
            indent=2,
        )
        if args.output:
            Path(args.output).write_text(output + "\n", encoding="utf-8")
        else:
            print(output)
    except (OSError, ValueError) as exc:
        print(f"chunk_document: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
