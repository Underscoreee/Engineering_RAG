#!/usr/bin/env python3
"""Search the configured Elasticsearch Chunk index with BM25."""

import argparse
import json
import sys

from engineering_rag.retrieval import (
    BM25Retriever,
    ElasticsearchSettings,
    create_elasticsearch_client,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", required=True)
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--index", help="Override ELASTICSEARCH_INDEX for this run")
    parser.add_argument("--standard-code")
    parser.add_argument("--clause-number")
    parser.add_argument("--document-id")
    parser.add_argument("--content-type")
    explanation = parser.add_mutually_exclusive_group()
    explanation.add_argument("--explanation", action="store_true")
    explanation.add_argument("--normative", action="store_true")
    args = parser.parse_args()
    filters = {
        key: value
        for key, value in {
            "standard_code": args.standard_code,
            "clause_number": args.clause_number,
            "document_id": args.document_id,
            "content_type": args.content_type,
        }.items()
        if value is not None
    }
    if args.explanation:
        filters["is_explanation"] = True
    elif args.normative:
        filters["is_explanation"] = False
    try:
        settings = ElasticsearchSettings.from_env()
        client = create_elasticsearch_client(settings)
        results = BM25Retriever(client, args.index or settings.index_name).search(
            args.query, top_k=args.top_k, filters=filters
        )
    except Exception as exc:
        print(f"BM25 search failed: {exc}", file=sys.stderr)
        return 1
    print(
        json.dumps(
            [result.model_dump(mode="json") for result in results],
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
