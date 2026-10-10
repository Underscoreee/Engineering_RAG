#!/usr/bin/env python3
"""Bulk index a Task 4.2 chunks.json file."""

import argparse
import json
import sys

from engineering_rag.retrieval import (
    ElasticsearchChunkIndexer,
    ElasticsearchSettings,
    create_elasticsearch_client,
)
from engineering_rag.retrieval.indexer import load_chunks


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to a chunks.json array")
    parser.add_argument("--index", help="Override ELASTICSEARCH_INDEX for this run")
    parser.add_argument(
        "--refresh", action="store_true", help="Refresh the index after each bulk request"
    )
    args = parser.parse_args()
    try:
        settings = ElasticsearchSettings.from_env()
        index_name = args.index or settings.index_name
        client = create_elasticsearch_client(settings)
        chunks = load_chunks(args.input)
        result = ElasticsearchChunkIndexer(
            client, index_name, refresh=args.refresh
        ).index_chunks(chunks, record_dataset_metadata=True)
    except Exception as exc:
        print(f"Failed to index Chunks: {exc}", file=sys.stderr)
        return 1
    print(result.model_dump_json(indent=2))
    return 1 if result.failure_count else 0


if __name__ == "__main__":
    raise SystemExit(main())
