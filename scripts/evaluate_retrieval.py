#!/usr/bin/env python3
"""Evaluate Elasticsearch BM25 against a versioned Golden Dataset."""

import argparse
import json
import sys
from pathlib import Path

from engineering_rag.evaluation import (
    GoldenDatasetValidator,
    RetrievalEvaluator,
    load_golden_dataset,
)
from engineering_rag.evaluation.dataset import golden_dataset_fingerprint
from engineering_rag.evaluation.evaluator import write_evaluation_report
from engineering_rag.evaluation.validator import write_validation_report
from engineering_rag.retrieval import (
    BM25Retriever,
    ElasticsearchSettings,
    create_elasticsearch_client,
)
from engineering_rag.retrieval.index_validation import validate_index_dataset
from engineering_rag.retrieval.indexer import (
    chunk_dataset_fingerprint,
    load_chunks,
)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dataset", required=True)
    parser.add_argument("--chunks", required=True)
    parser.add_argument("--output-dir", required=True)
    parser.add_argument("--index", help="Override ELASTICSEARCH_INDEX for this run")
    parser.add_argument("--candidate-pool", type=int, default=50)
    parser.add_argument(
        "--diagnostic",
        action="store_true",
        help="Write validation diagnostics for invalid data; never emits baseline metrics",
    )
    args = parser.parse_args()
    try:
        dataset = load_golden_dataset(args.dataset)
        chunks = load_chunks(args.chunks)
        validation = GoldenDatasetValidator().validate(dataset, chunks)
        write_validation_report(validation, args.output_dir)
        if not validation.is_valid:
            status = {
                "status": "INVALID_GOLDEN_DATASET",
                "baseline_status": "NOT_A_VALID_BASELINE",
                "diagnostic_mode": args.diagnostic,
                "invalid_targets": validation.invalid_targets,
            }
            destination = Path(args.output_dir)
            destination.mkdir(parents=True, exist_ok=True)
            (destination / "diagnostic_status.json").write_text(
                json.dumps(status, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            print(
                "Retrieval evaluation blocked: INVALID_GOLDEN_DATASET; "
                "NOT_A_VALID_BASELINE",
                file=sys.stderr,
            )
            return 2

        settings = ElasticsearchSettings.from_env()
        client = create_elasticsearch_client(settings)
        index_name = args.index or settings.index_name
        index_validation = validate_index_dataset(client, index_name, chunks)
        destination = Path(args.output_dir)
        destination.mkdir(parents=True, exist_ok=True)
        (destination / "index_validation.json").write_text(
            index_validation.model_dump_json(indent=2) + "\n",
            encoding="utf-8",
        )
        if not index_validation.is_valid:
            print(
                "Retrieval evaluation blocked: Elasticsearch index does not match "
                "the validated Chunk dataset",
                file=sys.stderr,
            )
            return 3

        info = client.info()
        report = RetrievalEvaluator(
            BM25Retriever(client, index_name), candidate_pool=args.candidate_pool
        ).evaluate(dataset)
        report["validation"] = {
            "valid_queries": validation.total_queries,
            "valid_targets": validation.valid_targets,
            "status": "VALID",
        }
        report["chunk_dataset"] = {
            "count": len(chunks),
            "fingerprint": chunk_dataset_fingerprint(chunks),
        }
        report["golden_dataset_fingerprint"] = golden_dataset_fingerprint(dataset)
        report["elasticsearch_version"] = info.get("version", {}).get("number")
        write_evaluation_report(report, args.output_dir)
    except Exception as exc:
        print(f"Retrieval evaluation failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(report["metrics"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
