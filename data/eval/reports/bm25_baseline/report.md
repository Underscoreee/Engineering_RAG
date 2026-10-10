# BM25 Retrieval Evaluation

- Dataset version: `example-v1-GB500010-2010`
- Dataset size: 9
- Elasticsearch index: `engineering_rag_chunks_v1`
- Index configuration: `{"mapping": "engineering_rag_chunks_v1", "text_analyzer": "engineering_standard (built-in standard)", "ranking": "Elasticsearch native BM25"}`
- Run time (UTC): `2026-10-09T08:13:02.300633+00:00`
- Query fields: `content^3, standard_name^2, standard_code^2, context_header^1`

## Overall metrics

| Metric | Value |
| --- | ---: |
| Recall@1 | 0.055556 |
| Precision@1 | 0.111111 |
| HitRate@1 | 0.111111 |
| Recall@3 | 0.055556 |
| Precision@3 | 0.037037 |
| HitRate@3 | 0.111111 |
| Recall@5 | 0.055556 |
| Precision@5 | 0.022222 |
| HitRate@5 | 0.111111 |
| Recall@10 | 0.055556 |
| Precision@10 | 0.011111 |
| HitRate@10 | 0.111111 |
| MRR@5 | 0.111111 |
| nDCG@5 | 0.068127 |
| MRR@10 | 0.111111 |
| nDCG@10 | 0.068127 |

## Metrics by query type

### simple

- Recall@1: 0.250000
- Precision@1: 0.500000
- HitRate@1: 0.500000
- Recall@3: 0.250000
- Precision@3: 0.166667
- HitRate@3: 0.500000
- Recall@5: 0.250000
- Precision@5: 0.100000
- HitRate@5: 0.500000
- Recall@10: 0.250000
- Precision@10: 0.050000
- HitRate@10: 0.500000
- MRR@5: 0.500000
- nDCG@5: 0.306574
- MRR@10: 0.500000
- nDCG@10: 0.306574

### limit

- Recall@1: 0.000000
- Precision@1: 0.000000
- HitRate@1: 0.000000
- Recall@3: 0.000000
- Precision@3: 0.000000
- HitRate@3: 0.000000
- Recall@5: 0.000000
- Precision@5: 0.000000
- HitRate@5: 0.000000
- Recall@10: 0.000000
- Precision@10: 0.000000
- HitRate@10: 0.000000
- MRR@5: 0.000000
- nDCG@5: 0.000000
- MRR@10: 0.000000
- nDCG@10: 0.000000

### concept

- Recall@1: 0.000000
- Precision@1: 0.000000
- HitRate@1: 0.000000
- Recall@3: 0.000000
- Precision@3: 0.000000
- HitRate@3: 0.000000
- Recall@5: 0.000000
- Precision@5: 0.000000
- HitRate@5: 0.000000
- Recall@10: 0.000000
- Precision@10: 0.000000
- HitRate@10: 0.000000
- MRR@5: 0.000000
- nDCG@5: 0.000000
- MRR@10: 0.000000
- nDCG@10: 0.000000

### formula

- Recall@1: 0.000000
- Precision@1: 0.000000
- HitRate@1: 0.000000
- Recall@3: 0.000000
- Precision@3: 0.000000
- HitRate@3: 0.000000
- Recall@5: 0.000000
- Precision@5: 0.000000
- HitRate@5: 0.000000
- Recall@10: 0.000000
- Precision@10: 0.000000
- HitRate@10: 0.000000
- MRR@5: 0.000000
- nDCG@5: 0.000000
- MRR@10: 0.000000
- nDCG@10: 0.000000

### colloquial

- Recall@1: 0.000000
- Precision@1: 0.000000
- HitRate@1: 0.000000
- Recall@3: 0.000000
- Precision@3: 0.000000
- HitRate@3: 0.000000
- Recall@5: 0.000000
- Precision@5: 0.000000
- HitRate@5: 0.000000
- Recall@10: 0.000000
- Precision@10: 0.000000
- HitRate@10: 0.000000
- MRR@5: 0.000000
- nDCG@5: 0.000000
- MRR@10: 0.000000
- nDCG@10: 0.000000

### synonym

- Recall@1: 0.000000
- Precision@1: 0.000000
- HitRate@1: 0.000000
- Recall@3: 0.000000
- Precision@3: 0.000000
- HitRate@3: 0.000000
- Recall@5: 0.000000
- Precision@5: 0.000000
- HitRate@5: 0.000000
- Recall@10: 0.000000
- Precision@10: 0.000000
- HitRate@10: 0.000000
- MRR@5: 0.000000
- nDCG@5: 0.000000
- MRR@10: 0.000000
- nDCG@10: 0.000000

### multi_clause

- Recall@1: 0.000000
- Precision@1: 0.000000
- HitRate@1: 0.000000
- Recall@3: 0.000000
- Precision@3: 0.000000
- HitRate@3: 0.000000
- Recall@5: 0.000000
- Precision@5: 0.000000
- HitRate@5: 0.000000
- Recall@10: 0.000000
- Precision@10: 0.000000
- HitRate@10: 0.000000
- MRR@5: 0.000000
- nDCG@5: 0.000000
- MRR@10: 0.000000
- nDCG@10: 0.000000

### explanation

- Recall@1: 0.000000
- Precision@1: 0.000000
- HitRate@1: 0.000000
- Recall@3: 0.000000
- Precision@3: 0.000000
- HitRate@3: 0.000000
- Recall@5: 0.000000
- Precision@5: 0.000000
- HitRate@5: 0.000000
- Recall@10: 0.000000
- Precision@10: 0.000000
- HitRate@10: 0.000000
- MRR@5: 0.000000
- nDCG@5: 0.000000
- MRR@10: 0.000000
- nDCG@10: 0.000000

## Missed queries

- `example-simple2`: 混凝土结构中结构缝的设计应符合什么要求？ — top result `example / 376058020cb669dfdc40c79b` (score 105.624540)
- `example-limit`: 板中受力钢筋的间距要求是多少？ — top result `example / e5e124dd925045de4b164bdc` (score 62.889800)
- `example-concept`: 什么是深梁？ — top result `example / bec5374ce26f68bd333aa567` (score 33.374030)
- `example-formula`: 示例公式是什么？ — top result `example / 3e26a6ede1ac62026ae400b4` (score 35.433056)
- `example-colloquial`: 这个东西平时怎么算？ — top result `example / 7690673b1806806bfe41c2a6` (score 36.299793)
- `example-synonym`: 示例同义表达 — top result `example / 5c157c7315044c37b56eb636` (score 36.768063)
- `example-multi-clause`: 哪些示例条文共同适用？ — top result `example / 8147c96ede73c52f3ad2e88e` (score 54.303276)
- `example-explanation`: 为什么作出这项示例规定？ — top result `example / f63ff06bda2387100c2f4b1a` (score 47.272140)

## Typical failures and possible causes

Inspect the ranked results in `per_query.json`. Common baseline causes include the built-in standard analyzer's limited Chinese term segmentation, vocabulary mismatch, missing or incorrect Chunk metadata, and incomplete human judgments.

Future experiments should be evaluated against the same versioned judgments before adopting analyzer, query, or ranking changes.
