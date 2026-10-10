# Elasticsearch BM25 retrieval

## Scope

Task 5 indexes each `Chunk` as one Elasticsearch document and retrieves it with
Elasticsearch's native BM25 score. It does not index complete PDFs as single records and
does not add vectors, embeddings, hybrid retrieval, reranking, query rewriting, or an LLM.

## Local Elasticsearch

The repository pins Elasticsearch Server 8.19.23 and `elasticsearch` Python client
8.19.2. Start the single-node service with:

```bash
docker compose -f docker-compose.elasticsearch.yml up -d
export ELASTICSEARCH_URL=http://127.0.0.1:9200
export ELASTICSEARCH_INDEX=engineering_rag_chunks_v1
```

The Compose port is bound to `127.0.0.1`, data is stored in a named volume, and security
is disabled for local development. This configuration must not be deployed to production.
A production deployment must enable TLS and authentication and supply credentials through
`ELASTICSEARCH_USERNAME` and `ELASTICSEARCH_PASSWORD`; credentials must not be committed.

## Mapping

`ElasticsearchChunkIndexer` creates an explicit, strict mapping. Searchable text fields
use the built-in `standard` analyzer. IDs, standard and clause codes, structure type,
flags, page range, and source block IDs retain exact typed fields for filtering and later
citation. Other `Chunk` metadata is also preserved. No vector field is created.

The built-in standard analyzer is a reproducible V1 baseline. Its Chinese word
segmentation is limited and may split specialist terms poorly. Analyzer changes require a
new index and evaluation against the same human judgments.

## Create and populate the index

```bash
python scripts/create_index.py
python scripts/index_chunks.py \
  --input data/debug/example_task5_1/chunks.json \
  --index engineering_rag_chunks_task5_1_v2 \
  --refresh
```

Creating an existing index is safe and does not delete data. Destructive recreation is
available only through the explicit `python scripts/create_index.py --recreate` flag.
Bulk writes use `chunk_id` as `_id`, so repeating the same input replaces the same records
instead of creating duplicates. The command prints success and failure counts and exits
nonzero if any item fails.

For a complete `chunks.json`, the indexing CLI verifies the final document count and
records the Chunk count, SHA-256 dataset fingerprint, and Mapping version in Mapping
`_meta`. Formal evaluation requires these values to match its local validated Chunk file.

## Search

```bash
python scripts/search_bm25.py \
  --query "混凝土强度等级有什么要求" \
  --top-k 5
```

Initial configurable field weights are `content^3`, `standard_name^2`,
`standard_code^2`, and `context_header^1`. They are experimental defaults.
Exact identifiers are separate structured filters:

```bash
python scripts/search_bm25.py \
  --query "强度等级" \
  --standard-code "GB 50010-2010" \
  --clause-number "4.2.3" \
  --normative
```

The library interface accepts the same exact filters through `BM25Retriever.search()`.
Future query understanding can populate these filters without changing the retriever's
input contract.

## Current limitations

- Only lexical BM25 retrieval is available.
- The standard analyzer has limited Chinese specialist term segmentation.
- Standard and clause identifiers are filtered only when supplied explicitly.
- There is no synonym dictionary, spelling correction, query understanding, or intent classifier.
- Retrieval quality is unknown until a real, human-reviewed Golden Dataset is evaluated.
