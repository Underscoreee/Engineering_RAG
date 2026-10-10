# Retrieval evaluation

## Golden Dataset

A Golden Dataset is a versioned JSON document containing human-authored questions and
human-confirmed relevance judgments against real `Chunk` data. Each query records a
`query_type` for grouped reporting; it does not invoke an intent classifier.

Supported query types are free labels and can cover simple, limit, concept, formula,
colloquial, synonym, multi-clause, and explanation questions. Each target stores:

- `document_id`
- `clause_number`, when one exists
- `is_explanation`
- optional `content_type`
- graded `relevance`: 0, 1, or 2

For content without a clause number, provide either `logical_chunk_id` or a stable list of
`source_block_ids`. A bare document ID is rejected because it could match unrelated text.
The example under `data/eval/` contains invented records for schema and pipeline testing;
it is not evidence of retrieval quality.

## Logical matching and deduplication

Evaluation matches clauses by document ID, clause number, explanation flag, and optional
content type. Consequently, equal clause numbers in different standards never match, and
normative text does not match its clause explanation. Content without a clause uses its
logical Chunk ID or exact source block locator.

Before applying K, repeated physical results with the same document, clause or fallback
locator, explanation flag, and content type are collapsed in rank order. A relevance
target can be credited only once. This prevents a long clause split into several physical
Chunks from inflating metrics.

Before formal scoring, `GoldenDatasetValidator` checks every target against the exact
Chunk collection. It reports missing documents or clauses, explanation and content type
mismatches, ambiguous logical sources, and duplicate targets. Suggested fixes are clues
for human review and are never applied automatically. Any invalid target blocks formal
metric generation.

## Metrics

- **Physical metrics** take the first K Elasticsearch Chunk hits. Duplicate Chunks from
  one logical clause occupy positions, while that clause receives relevance credit once.
- **Logical metrics** deduplicate a physical candidate pool by logical source before taking
  K. The baseline candidate pool is 50; reports record when it contains fewer than K
  distinct logical sources.
- Both rankings calculate Recall, Precision, HitRate, MRR, and graded nDCG. Output names
  explicitly include `physical_` or `logical_`, such as `physical_recall_at_5` and
  `logical_recall_at_5`.

Dataset metrics are arithmetic means over queries. Empty datasets and queries without a
positive judgment are rejected instead of receiving a misleading zero score.

## Run an evaluation

After indexing the same Chunk collection used for annotation:

```bash
export ELASTICSEARCH_URL=http://127.0.0.1:9200
export ELASTICSEARCH_INDEX=engineering_rag_chunks_v1
python scripts/evaluate_retrieval.py \
  --dataset data/eval/golden_dataset.json \
  --chunks data/debug/example_task5_1/chunks.json \
  --index engineering_rag_chunks_task5_1_v2 \
  --output-dir data/eval/reports/bm25_task5_1
```

The output directory contains:

- `metrics.json`: dataset version, index, query configuration, run time, overall metrics,
  and metrics grouped by query type.
- `per_query.json`: each query's metrics and ranked retrieval results for diagnosis.
- `report.md`: experiment summary, misses, typical causes, and follow-up directions.

Record the Golden Dataset version, source Chunk export, index mapping, field weights, and
run time together. Do not compare or claim improvements using the illustrative example or
different untracked judgments.

If validation fails, the CLI writes `validation_report.json` and
`diagnostic_status.json`, marks the run `INVALID_GOLDEN_DATASET` and
`NOT_A_VALID_BASELINE`, and does not create metrics.
