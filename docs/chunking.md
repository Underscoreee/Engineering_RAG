# 结构感知 Chunking

## 目标

`EngineeringChunker` 将 Task 3 的 `DocumentStructure` 转成包含原文、结构上下文和来源的 `Chunk` 列表。输出面向后续检索、引用和评估；本模块不连接任何检索服务或模型。

不采用固定 token 数作为主要切分策略，因为它可能把条文、编号和适用条件从语义上切开。策略优先保留规范语义边界、条文完整性和上下文，再在超长内容上控制长度。

## Clause-first 分组

普通 Clause 是主要逻辑单元。Clause 后的普通段落和短注并入当前 Clause，直到下一个 Clause 或新的章/节上下文边界。不同 Clause 不合并。章、节作为上下文，不单独生成普通 Chunk；没有当前 Clause 的普通段落仍会生成 paragraph Chunk。

Chunk 不因页面变化而切分。`page_start`、`page_end` 由所有来源块的页码范围计算，因此跨页条文仍可保留为同一逻辑 Chunk。

## Note 和条文说明

短注（默认估算不超过 80 tokens）并入当前 Clause。长注独立成为 `content_type="note"` 的 Chunk，并通过 `parent_chunk_id` 指向 Clause Chunk。阈值可通过 `EngineeringChunker(short_note_max_tokens=...)` 调整。

条文说明与正文隔离，输出 `content_type="explanation"`、`is_explanation=true` 的 Chunk。无正文内容的 explanation heading 只作为分组状态节点，不单独生成 Chunk。

附录作为结构上下文保留；`appendix_section` 标题可以生成 paragraph Chunk，其 section path 包含附录和小节路径。

## 超长内容

默认 `max_tokens=800`，可通过 `EngineeringChunker(max_tokens=...)` 或 CLI 参数调整。超长 Clause 先按原 StructuredBlock 边界打包（通常对应段落），单个超长 block 再按句末标点切分；单句仍超长时才使用 token window。拆分子块沿用 Clause 的编号、路径和章节元数据，并共享稳定的 `logical_chunk_id`。

`TokenCounter` 是确定性的轻量估算器：CJK 字符、英文/数字词组和标点分别计数。它不是具体 embedding 模型 tokenizer 的精确替代品，后续可替换。

## 上下文、内容和来源

- `content` 保存 StructuredBlock 原文；context header 不写入其中。
- `context_header` 独立保存规范名称/编号、章、节和条文路径。
- `embedding_text` 为 context header、空行和原文的组合，供后续 embedding 使用。
- `source_block_ids` 使用 `p{page_number}_block_{source_block_number}` 追溯源块。
- `chunk_id` 通过 SHA-256 对 document ID、content type、来源块和逻辑位置生成，重复输入会得到相同 ID。

`is_mandatory` 当前固定为 `False`，不从“应”“必须”等词推断强制性。表格、公式、图纸目前仅保留 Chunk schema 的关联 ID 字段；后续可接入专门解析器和结构化来源表示。本阶段不做 OCR、向量、BM25、数据库、重排、生成或查询处理。

## Task 4.1 数据流与工程规则

完整处理链路为：

```text
PDF
↓
PdfParser
↓
Document
↓
StructureParser
↓
DocumentStructure
↓
EngineeringChunker
↓
Chunk[]
```

`PdfParser.parse()` 可接收调用方提供的 `standard_name` 和 `standard_code`，不会根据文件名或正文猜测。`StructureParser` 将这些元数据以及 `source_file` 原样传给 `DocumentStructure`，Chunker 再将规范信息写入独立的 `context_header`。

StructureParser 仍保留并标记 header/footer 原始块；Chunker 忽略它们，且跳过时不结束当前 Clause，避免页眉页脚产生噪声 Chunk 或切断跨页正文。

超长 Clause 的多个物理 Chunk 使用相同且稳定的 `logical_chunk_id` 表示属于同一逻辑条文。`parent_chunk_id` 只表示实际存在的父 Chunk，例如长注指向其 Clause Chunk；Clause 拆分片段之间不伪造父子关系。

Context Header 优先采用完整 `section_path`，保留原始层级顺序并去重；只有路径为空时才回退到 chapter、section 和 clause 字段。缺少的规范名称或编号会省略，不会输出 `None`。

`tests/integration/test_pdf_to_chunk_pipeline.py` 使用 PyMuPDF 在测试运行时生成四页 PDF，并实际依次调用 PdfParser、StructureParser 和 EngineeringChunker。测试验证规范元数据贯穿、header/footer 未进入 Chunk、正文与条文说明隔离、页码范围和来源 ID 可追溯，以及 context 与原文分别保存在正确字段中。

## CLI

输入 `StructureParser` JSON：

```bash
python scripts/chunk_document.py structure.json
python scripts/chunk_document.py structure.json --output chunks.json --max-tokens 800
```
