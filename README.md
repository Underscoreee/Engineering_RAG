# Engineering RAG

面向工程标准文档的检索增强问答系统。

## 当前阶段

Task 1：项目骨架、基础配置、Chunk 数据模型及其单元测试。
Task 2：PyMuPDF PDF 解析。
Task 3：工程规范结构识别。
Task 4：基于规范结构的智能 Chunking。
Task 4.1：Chunking 工程化收尾与 PDF 到 Chunk 集成测试。
Task 4.2：真实工程规范 PDF 端到端检查与导出工具。

当前正在实现 Task 5.1：真实规范结构修复、Golden Dataset 校验与 BM25 基线重测。

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

## BM25 本地基线

本地 Elasticsearch 固定使用 8.19.23，配置仅监听 `127.0.0.1` 并关闭认证：

```bash
docker compose -f docker-compose.elasticsearch.yml up -d
export ELASTICSEARCH_URL=http://127.0.0.1:9200
export ELASTICSEARCH_INDEX=engineering_rag_chunks_v1
python scripts/create_index.py
python scripts/index_chunks.py --input data/debug/example/chunks.json --refresh
python scripts/search_bm25.py --query "什么是深梁？" --top-k 5
```

本地 Compose 配置不得用于生产环境。生产连接需要由
`ELASTICSEARCH_URL`、`ELASTICSEARCH_USERNAME`、`ELASTICSEARCH_PASSWORD`
和 `ELASTICSEARCH_INDEX` 提供，并启用认证与 TLS。

评估方法、人工标注要求和报告格式见 `docs/evaluation.md`。仓库中的
`golden_dataset.example.json` 只用于演示 Schema，不能用于检索质量声明。

Task 5.1 的真实规范重新生成与校验：

```bash
python scripts/inspect_real_pdf.py data/raw/example.pdf \
  --standard-name "混凝土结构设计规范" \
  --standard-code "GB 50010-2010" \
  --output-dir data/debug/example_task5_1 \
  --compare-with data/debug/example/summary.json

python scripts/validate_golden_dataset.py \
  --dataset data/eval/golden_dataset.json \
  --chunks data/debug/example_task5_1/chunks.json \
  --output-dir data/eval/validation_task5_1
```

正式评估必须同时通过 Golden Dataset 校验以及 Elasticsearch 索引数量、
Chunk 指纹和 Mapping 版本校验。无效标注会阻止指标生成。


我要重新组织开发流程，这次不再把整个RAG系统当成一个整体来开发，这样每次改动牵一发而动全身，将整个系统拆分成若干个独立的微服务，服务内部独立开发、测试、对外暴露函数调用接口，实现功能解耦。
预期拆分为以下几个服务：
1、PDF文档解析服务，实现功能：将PDF格式的规范文档进行结构化解析，最终输出结构化的document文档。每个文档都有标准名称、标准代码、标准内容等，标准内容每一页包含页面分析结果（外封面、内封面、发布公告、前言、中文目次、英文目次、正文、用词说明、引用标准名录、条文说明封面、修订说明、条文说明目次、条文说明正文），分析为正文和条文说明正文的页面内容保留文档层级结构，并按照条目进行结构化拆分，例如4.2.1、4.2.2等。
2、chunking模块，实现功能：根据结构化document文档直接构造chunk。
3、关键词检索模块，实现功能：使用Elasticsearch数据库，可以根据chunk的内容进行BM25的关键词检索，召回指定数量的相关chunk。
4、条件检索模块，实现功能：根据chunk保留的结构化数据，如正文的条文序号、正文的章节序号、正文的章节名称、条文说明正文的条文序号、条文说明正文的章节序号、条文说明正文的条文序号等进行条件过滤，召回满足条件的chunk。
5、向量检索模块，实现功能