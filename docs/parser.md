# PDF 文本解析器

## 职责

`PdfParser` 使用 PyMuPDF 从带有文本层的数字 PDF 中提取页面全文和文本块，并返回可 JSON 序列化的 `Document`。调用方式：

```python
from engineering_rag.ingestion.parser import PdfParser

document = PdfParser().parse("example.pdf")
json_text = document.model_dump_json(indent=2)
```

解析器使用 `pymupdf.open()` 打开文件，并在解析完成或发生错误时关闭文档资源。页面文本通过 `page.get_text("text", sort=True)` 获取；文本块通过 `page.get_text("blocks", sort=True)` 获取。

## 数据结构

- `Document`：`document_id`（输入文件名 stem）、`source_file`、`page_count` 和 `pages`。
- `Page`：PDF 内的 `page_number`、页面完整文本 `text` 和 `blocks`。
- `TextBlock`：文本 `text`、边界框 `bbox`、`block_number` 和 `block_type`。

`page_number` 使用 1-based 序号，表示 PDF 文件内部页序，不代表印刷页面上的页码。`bbox` 按 `[x0, y0, x1, y1]` 保存，坐标来自 PyMuPDF 的 PDF 页面坐标。

## 支持范围与限制

当前支持有文本层的数字 PDF。空白文本块会被忽略，空白页面保留并返回空文本和空块列表。文件不存在时抛出 `FileNotFoundError`，无法打开或解析时抛出 `PdfParseError`。

当前不支持 OCR、表格/公式/图像识别或扫描件文本提取。阅读顺序依赖 PyMuPDF 的 `sort=True`，复杂版面可能无法完全符合人工阅读顺序；扫描件或无文本层页面不会自动识别内容。`document_id` 暂以文件名 stem 生成，不保证跨目录唯一。
