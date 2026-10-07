# 工程规范结构解析

## 职责和数据流

`StructureParser` 接收 Task 2 的 `Document`，按页面和原始文本块顺序识别常见工程规范结构，返回 `DocumentStructure`。它只为块添加结构角色和层级，不拆分或合并文本，也不改变原始 PDF：

```text
PDF → PdfParser → Document / TextBlock → StructureParser → DocumentStructure
```

`TextBlock` 保留原有 `text`、`bbox`、`block_number`、`block_type`，并新增 `font_size`、`font_name` 和 `is_bold`。样式信息从 `page.get_text("dict", sort=True)` 的 `blocks → lines → spans` 提取；字符数最多的 span 样式作为该块的代表样式。完整 spans 不保存在模型中。原有 `page.get_text("blocks", sort=True)` 仍负责文本块内容、边界框和编号。

## 结构模型和识别

`StructuredBlock` 包含源页码、原文、bbox、`StructureRole`、当前章/节、条文号、层级路径、条文说明状态和源 block 编号。`DocumentStructure` 保存 `document_id` 和按阅读顺序排列的结构块。

角色使用 `StructureRole` 枚举，包括 document title、chapter、section、clause、paragraph、note、appendix、appendix section、explanation heading、header、footer 和 unknown。

- 章：中文“第一章 总则”或数字“4 基本设计规定”。
- 文档标题：仅将文档首个块中字号至少 18 且判定为粗体的文本作为候选标题。
- 节：`N.N`，并要求编号后不是另一个点、字母或连字符；因此 `4.1.1` 不会被当成节。
- 条：`N.N.N`，可带正文；更复杂的编号形式不会截取部分编号，而归为 unknown。
- 附录：`附录 A`；附录小节：`A.1`。
- 注：以“注：”“注1：”“注 1：”等形式开头。
- 普通未编号文本默认为 paragraph；未支持的多级编号归为 unknown，原文保留。

## 层级路径和条文说明

解析过程维护 `current_chapter`、`current_section`、`current_clause` 和 `explanation_mode`。遇到章或附录时重置下级状态；遇到节时清除当前条文；遇到条时更新当前条文号。路径依次包含当前章、节、条，例如：

```json
["4 基本设计规定", "4.2 材料", "4.2.3"]
```

识别到“条文说明”标题后进入 explanation mode，后续块标记 `is_explanation=true`，直到遇到新的章或附录标题。识别不确定时保留原文，不删除块。

## 页眉页脚

仅当相同文本至少出现在两个页面，并且 bbox 位于非常靠近页面顶端或底端的保守坐标范围内，才标记为 header/footer。原始块始终保留；不满足条件的块不会因页面位置而被移除。

## 已知限制

规则只覆盖常见编号与标题形式，不是所有工程标准的通用语法。字体、特殊编号、无标题正文和版式变化可能导致 unknown 或 paragraph。页眉页脚的位置判断受页面尺寸影响，特意采取保守阈值。阅读顺序继续依赖 PyMuPDF 的 `sort=True`；它不能保证所有复杂多栏 PDF 的完美阅读顺序，复杂多栏结构属于后续增强。

当前不做 Chunking，因为本阶段只负责保留原始文本块并标注结构边界；分块策略需独立设计和测试，避免把结构识别与检索粒度耦合在一起。
