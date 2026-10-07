# 已知限制

- 当前 Pipeline 仅处理具有可提取文本层的数字 PDF。扫描件和文本层不足的 PDF 只会在检查摘要中标为“可能是扫描件”；当前未实现 OCR。
- PyMuPDF 的 `sort=True` 不能保证复杂多栏页面、浮动文本和非线性阅读顺序的结果完全正确。
- StructureParser 只覆盖常见工程规范标题和编号。特殊条文编号可能被保留为 unknown 或 paragraph，供后续独立任务处理。
- 复杂表格、公式、图纸和图像不会被专门解析；相关 Chunk metadata 预留但不会填充。
- TokenCounter 是轻量且可重复的估算器，不等同于任何未来 embedding 模型的 tokenizer。
