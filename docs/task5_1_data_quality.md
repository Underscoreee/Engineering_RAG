# Task 5.1 data quality and baseline protocol

## Hidden clause boundaries

PyMuPDF block extraction follows page layout rather than engineering semantics. One
`TextBlock` can contain the end of one paragraph, `3.2.2` on a separate visual line, and
the new clause text. Classifying only the start of the block misses that clause.

`LogicalLineSplitter` scans line starts for conservative structural patterns. It splits
clear clauses and headings while retaining adjacent ordinary lines. All effective source
text must reconstruct exactly after whitespace normalization.

## Provenance and explanation state

Every `LogicalSegment` retains `page_number`, `source_block_number`, the original block
`bbox`, and `segment_index`. The bbox remains the source block box; no line coordinates
are invented. Segment-aware source IDs and Chunk IDs are deterministic across runs.

The exact `条文说明` heading enters explanation mode. Ordinary chapters, sections, and
page transitions retain it. Repeated margin text cannot mutate the state, and an exact
semantic boundary is required to exit.

## Golden Dataset validation

Each target must resolve against generated Chunks by document, clause or stable source
locator, explanation flag, and optional content type. Multiple physical Chunks are valid
only when they share one logical source. Missing, ambiguous, duplicated, or mismatched
targets require human review. Retrieval output is never promoted to a judgment.

An invalid target changes the run status to `INVALID_GOLDEN_DATASET` and
`NOT_A_VALID_BASELINE`. Recall cannot be interpreted when its denominator contains answers
that do not exist in the evaluated corpus.

## Physical and logical ranking

Physical Recall@K uses the first K Elasticsearch hits; repeated pieces of a split clause
consume positions. Logical Recall@K first deduplicates a declared physical candidate pool
and then takes K logical sources. Reports record candidate shortage explicitly.

## Rebuild and reproduce

```bash
python scripts/inspect_real_pdf.py data/raw/example.pdf \
  --output-dir data/debug/example_task5_1 \
  --compare-with data/debug/example/summary.json

python scripts/validate_golden_dataset.py \
  --dataset data/eval/golden_dataset.json \
  --chunks data/debug/example_task5_1/chunks.json \
  --output-dir data/eval/validation_task5_1

export ELASTICSEARCH_URL=http://127.0.0.1:9200
python scripts/create_index.py --index engineering_rag_chunks_task5_1_v2
python scripts/index_chunks.py \
  --input data/debug/example_task5_1/chunks.json \
  --index engineering_rag_chunks_task5_1_v2 \
  --refresh

python scripts/evaluate_retrieval.py \
  --dataset data/eval/golden_dataset.json \
  --chunks data/debug/example_task5_1/chunks.json \
  --index engineering_rag_chunks_task5_1_v2 \
  --output-dir data/eval/reports/bm25_task5_1
```

Indexing records the complete Chunk count, dataset fingerprint, and Mapping version. The
evaluation CLI compares them before scoring. A valid report also records Elasticsearch
version, Golden Dataset fingerprint, BM25 fields and weights, and candidate pool.
