# Engineering RAG

面向工程标准文档的检索增强问答系统。

## 当前阶段

Task 1：项目骨架、基础配置、Chunk 数据模型及其单元测试。
Task 2：PyMuPDF PDF 解析。
Task 3：工程规范结构识别。
Task 4：基于规范结构的智能 Chunking。
Task 4.1：Chunking 工程化收尾与 PDF 到 Chunk 集成测试。
Task 4.2：真实工程规范 PDF 端到端检查与导出工具。

Task 5（BM25、Golden Dataset、Recall@K）尚未开始。

## 创建虚拟环境

需要 Python 3.11 或更高版本：

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
```

## 运行测试

```bash
python -m pytest
```

## Real PDF Inspection

将带有文本层的工程规范 PDF 放入 `data/raw/`，然后执行完整本地 Pipeline：

```bash
python scripts/inspect_real_pdf.py data/raw/example.pdf \
  --standard-name "混凝土结构设计规范" \
  --standard-code "GB 50010-2010" \
  --output-dir data/debug/example
```

输出目录包含 `summary.json`、`document.json`、`structure.json`、`chunks.json`、`chunks.md` 和 `raw_text.txt`。当前版本仅支持有文本层的 PDF；工具会提示可能是扫描件或文本层不足的文件，但不会执行 OCR。
