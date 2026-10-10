# Engineering RAG Project

## Project Goal

Build an engineering-standard RAG question answering system.

Main pipeline:

PDF
-> Parsing
-> OCR
-> Structure extraction
-> Chunking
-> Embedding
-> Milvus
-> Elasticsearch BM25
-> Query processing
-> Hybrid retrieval
-> Reranking
-> LLM generation
-> Citation validation
-> Evaluation

## Current Development Stage

This project is developed incrementally.

Do NOT implement the whole system at once.

Each task must:
1. Make the smallest necessary change.
2. Define clear input/output contracts.
3. Add tests.
4. Run tests.
5. Fix failures before finishing.
6. Avoid modifying unrelated modules.

## Engineering Rules

1. Do not implement the entire system in one task.
2. Work in small, independently testable modules.
3. Every non-trivial module must have unit tests.
4. Every feature must have a clear input/output contract.
5. Do not silently change existing APIs.
6. Do not hard-code model paths, database URLs, or API keys.
7. Use environment variables or configuration files.
8. Keep ingestion, retrieval, query processing, generation, and evaluation loosely coupled.
9. Prefer interfaces/adapters for external models and databases.
10. Preserve document metadata throughout the retrieval pipeline.
11. Every Chunk must preserve enough metadata for later citation.
12. Every production bug should receive a regression test.
13. Never claim retrieval quality improvements without evaluation results.
14. Run tests before declaring a task complete.
15. Do not modify unrelated files.
16. 不要为了满足 Chunk 大小而破坏规范语义边界

## Current Development Stage

Completed:

- Task 1: Project skeleton + Chunk model
- Task 2: PyMuPDF PDF parser
- Task 3: Engineering-standard structure parsing
- Task 4: Structure-aware Chunking
- Task 4.1: Chunking engineering cleanup
- Task 4.2: Real PDF end-to-end inspection tool
- Task 4.3: Engineering standard document region filtering

Current:

- Task 5.1: Real structure repair + Golden Dataset validation + BM25 baseline retest

Task-specific constraints for the current task should be defined in the user request.

Do not implement Elasticsearch or BM25 until Task 5 is explicitly requested.

Do not implement future tasks unless explicitly requested.

## Coding Style

- Python 3.11+
- Type hints
- Pydantic for data models
- pytest for testing
- Ruff for linting when appropriate
- Small functions
- Explicit error handling
- Structured logging

## Chunk Requirements

Chunk must contain at least:

- chunk_id
- document_id
- content
- page_start
- page_end
- standard_name
- standard_code
- clause_number
- section_path
- content_type
- is_mandatory
- is_explanation
- chapter
- section
- source_block_ids
- context_header
- embedding_text
- token_count
- parent_chunk_id
- logical_chunk_id
- table_id
- figure_id
- formula_id

Chunk metadata must remain suitable for later:

- vector retrieval
- BM25 retrieval
- reranking
- citation
- evaluation

## Development Workflow

For every task:

1. Inspect existing files.
2. Explain the implementation approach briefly.
3. Implement the smallest necessary change.
4. Add or update tests.
5. Run relevant tests.
6. Fix failures.
7. Report:
   - files changed
   - tests executed
   - test results
   - remaining limitations

Do not implement future tasks unless explicitly requested.
