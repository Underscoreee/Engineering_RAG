# Golden Dataset validation

- Dataset version: `example-v1-GB500010-2010`
- Total queries: 9
- Total targets: 16
- Valid targets: 9
- Invalid targets: 7
- Valid target coverage: 56.25%
- Status: `INVALID_GOLDEN_DATASET`

## Invalid targets

### example-formula / target 0

- Status: `CONTENT_TYPE_MISMATCH`
- Reason: The locator exists, but its content_type does not match.
- Target: `{"document_id":"example","clause_number":"11.1.7","is_explanation":false,"relevance":2,"content_type":"formula","logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Available content_type: clause

### example-formula / target 1

- Status: `CONTENT_TYPE_MISMATCH`
- Reason: The locator exists, but its content_type does not match.
- Target: `{"document_id":"example","clause_number":"8.3.1","is_explanation":false,"relevance":2,"content_type":"formula","logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Available content_type: clause

### example-colloquial / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '3.0.2' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"3.0.2","is_explanation":false,"relevance":1,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: K.0.2
- Possible clue: Nearby clause_number: J.0.2
- Possible clue: Nearby clause_number: H.0.2
- Possible clue: Nearby clause_number: G.0.2
- Possible clue: Nearby clause_number: F.0.2

### example-synonym / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '4.0.1' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"4.0.1","is_explanation":false,"relevance":1,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: K.0.1
- Possible clue: Nearby clause_number: J.0.1
- Possible clue: Nearby clause_number: H.0.1
- Possible clue: Nearby clause_number: G.0.1
- Possible clue: Nearby clause_number: F.0.1

### example-multi-clause / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '5.0.1' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"5.0.1","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: K.0.1
- Possible clue: Nearby clause_number: J.0.1
- Possible clue: Nearby clause_number: H.0.1
- Possible clue: Nearby clause_number: G.0.1
- Possible clue: Nearby clause_number: F.0.1

### example-multi-clause / target 1

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '5.0.2' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"5.0.2","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: K.0.2
- Possible clue: Nearby clause_number: J.0.2
- Possible clue: Nearby clause_number: H.0.2
- Possible clue: Nearby clause_number: G.0.2
- Possible clue: Nearby clause_number: F.0.2

### example-explanation / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '6.0.1' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"6.0.1","is_explanation":true,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: K.0.1
- Possible clue: Nearby clause_number: J.0.1
- Possible clue: Nearby clause_number: H.0.1
- Possible clue: Nearby clause_number: G.0.1
- Possible clue: Nearby clause_number: F.0.1

