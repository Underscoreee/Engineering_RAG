# Task 5.1 baseline comparison

## Data structure

| Measure | Historical output | Task 5.1 output |
| --- | ---: | ---: |
| Total Chunks | 4,724 | 1,638 |
| Clause blocks | 44 | 868 |
| Paragraph blocks | 5,160 | 4,657 |
| Explanation blocks | 8 | 1,564 |
| Clause Chunks | 60 | 517 |
| Paragraph Chunks | 4,607 | 500 |
| Explanation Chunks | 7 | 602 |

The counts are diagnostic observations rather than target thresholds. The large change is
explained by exposing clause boundaries inside multi-line TextBlocks and preserving
explanation mode through numbered chapters and sections.

## Golden Dataset validity

| Measure | Historical Chunks | Task 5.1 Chunks |
| --- | ---: | ---: |
| Total annotated targets in the current file | 16 | 16 |
| Valid targets | 1 | 9 |
| Valid target coverage | 6.25% | 56.25% |

Seven targets still require human review. They were not rewritten automatically.

## Retrieval metrics

The prior report is a **Historical invalid baseline** because 15 of the current 16 targets
could not match the historical Chunk collection. Its saved Recall@5 value must not be
interpreted as reliable BM25 quality.

Task 5.1 does not publish new Recall, MRR, or nDCG values because the Golden Dataset still
contains seven invalid targets. The evaluation CLI emitted `INVALID_GOLDEN_DATASET` and
`NOT_A_VALID_BASELINE` and stopped before scoring. The two runs therefore cannot be used
to claim a BM25 improvement.

The new Elasticsearch index `engineering_rag_chunks_task5_1_v2` contains 1,638 documents and
matches the generated Chunk count, SHA-256 fingerprint, and mapping version.
