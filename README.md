# Engineering RAG

面向工程标准文档的检索增强问答系统。

## 当前阶段

Task 1：项目骨架、基础配置、Chunk 数据模型及其单元测试。
Task 2：PyMuPDF PDF 解析。
Task 3：工程规范结构识别。
Task 4：基于规范结构的智能 Chunking。

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
