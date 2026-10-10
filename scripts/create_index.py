#!/usr/bin/env python3
"""Create the configured Elasticsearch Chunk index."""

import argparse
import sys

from engineering_rag.retrieval import (
    ElasticsearchChunkIndexer,
    ElasticsearchSettings,
    create_elasticsearch_client,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--recreate",
        action="store_true",
        help="Explicitly delete and recreate the configured index",
    )
    parser.add_argument("--index", help="Override ELASTICSEARCH_INDEX for this run")
    args = parser.parse_args()
    try:
        settings = ElasticsearchSettings.from_env()
        client = create_elasticsearch_client(settings)
        index_name = args.index or settings.index_name
        ElasticsearchChunkIndexer(client, index_name).create_index(args.recreate)
    except Exception as exc:
        print(f"Failed to create Elasticsearch index: {exc}", file=sys.stderr)
        return 1
    print(index_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
