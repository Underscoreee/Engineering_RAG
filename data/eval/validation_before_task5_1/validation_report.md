# Golden Dataset validation

- Dataset version: `example-v1-GB500010-2010`
- Total queries: 9
- Total targets: 16
- Valid targets: 1
- Invalid targets: 15
- Valid target coverage: 6.25%
- Status: `INVALID_GOLDEN_DATASET`

## Invalid targets

### example-simple1 / target 1

- Status: `EXPLANATION_MISMATCH`
- Reason: The locator exists, but its is_explanation value does not match.
- Target: `{"document_id":"example","clause_number":"3.5.4","is_explanation":true,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Available is_explanation: False

### example-simple2 / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '3.2.2' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"3.2.2","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 9.2.2
- Possible clue: Nearby clause_number: 3.4.2
- Possible clue: Nearby clause_number: 2.2.2
- Possible clue: Nearby clause_number: 6.2.22
- Possible clue: Nearby clause_number: 9.2.9

### example-simple2 / target 1

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '3.2.2' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"3.2.2","is_explanation":true,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 9.2.2
- Possible clue: Nearby clause_number: 3.4.2
- Possible clue: Nearby clause_number: 2.2.2
- Possible clue: Nearby clause_number: 6.2.22
- Possible clue: Nearby clause_number: 9.2.9

### example-limit / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '9.1.3' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"9.1.3","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 9.1.6
- Possible clue: Nearby clause_number: 9.1.4
- Possible clue: Nearby clause_number: 6.1.3
- Possible clue: Nearby clause_number: 9.2.13
- Possible clue: Nearby clause_number: 9.6.4

### example-concept / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '2.1.2' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"2.1.2","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 2.2.2
- Possible clue: Nearby clause_number: 9.2.1
- Possible clue: Nearby clause_number: 9.1.6
- Possible clue: Nearby clause_number: 9.1.4
- Possible clue: Nearby clause_number: 8.1.1

### example-concept / target 1

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number 'G.0.1' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"G.0.1","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 9.2.1
- Possible clue: Nearby clause_number: 8.5.1
- Possible clue: Nearby clause_number: 4.2.1

### example-concept / target 2

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number 'G.0.7' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"G.0.7","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 4.1.7

### example-concept / target 3

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number 'G.0.8' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"G.0.8","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`

### example-formula / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '11.1.7' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"11.1.7","is_explanation":false,"relevance":2,"content_type":"formula","logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 11.1.6
- Possible clue: Nearby clause_number: 11.1.4
- Possible clue: Nearby clause_number: 11.4.17
- Possible clue: Nearby clause_number: 4.1.7
- Possible clue: Nearby clause_number: 11.8.3

### example-formula / target 1

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '8.3.1' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"8.3.1","is_explanation":false,"relevance":2,"content_type":"formula","logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 8.5.1
- Possible clue: Nearby clause_number: 8.1.1
- Possible clue: Nearby clause_number: 9.3.10
- Possible clue: Nearby clause_number: 9.2.1
- Possible clue: Nearby clause_number: 4.2.1

### example-colloquial / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '3.0.2' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"3.0.2","is_explanation":false,"relevance":1,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 3.4.2
- Possible clue: Nearby clause_number: 3.3.2
- Possible clue: Nearby clause_number: 5.6.2
- Possible clue: Nearby clause_number: 3.5.4
- Possible clue: Nearby clause_number: 3.5.3

### example-synonym / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '4.0.1' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"4.0.1","is_explanation":false,"relevance":1,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 4.2.1
- Possible clue: Nearby clause_number: 9.2.1
- Possible clue: Nearby clause_number: 8.5.1
- Possible clue: Nearby clause_number: 4.2.9
- Possible clue: Nearby clause_number: 4.2.5

### example-multi-clause / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '5.0.1' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"5.0.1","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 9.2.1
- Possible clue: Nearby clause_number: 8.5.1
- Possible clue: Nearby clause_number: 5.6.3
- Possible clue: Nearby clause_number: 5.6.2
- Possible clue: Nearby clause_number: 5.2.5

### example-multi-clause / target 1

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '5.0.2' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"5.0.2","is_explanation":false,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 5.6.2
- Possible clue: Nearby clause_number: 5.6.3
- Possible clue: Nearby clause_number: 5.2.5
- Possible clue: Nearby clause_number: 3.4.2
- Possible clue: Nearby clause_number: 3.3.2

### example-explanation / target 0

- Status: `CLAUSE_NOT_FOUND`
- Reason: clause_number '6.0.1' was not found in the specified document.
- Target: `{"document_id":"example","clause_number":"6.0.1","is_explanation":true,"relevance":2,"content_type":null,"logical_chunk_id":null,"source_block_ids":[]}`
- Possible clue: Nearby clause_number: 6.4.14
- Possible clue: Nearby clause_number: 6.2.16
- Possible clue: Nearby clause_number: 9.2.1
- Possible clue: Nearby clause_number: 8.5.1
- Possible clue: Nearby clause_number: 6.2.3

