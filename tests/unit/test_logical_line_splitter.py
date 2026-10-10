from engineering_rag.ingestion.logical_line_splitter import LogicalLineSplitter
from engineering_rag.ingestion.parser import TextBlock


def block(text: str) -> TextBlock:
    return TextBlock(
        text=text,
        bbox=[10.0, 20.0, 500.0, 120.0],
        block_number=7,
        block_type=0,
        font_size=12.0,
        font_name="TestFont",
    )


def test_splits_standalone_and_inline_clause_boundaries() -> None:
    segments = LogicalLineSplitter().split(
        23,
        block(
            "上一条正文。\n3.2.2\n本条规定建筑结构应满足要求。\n"
            "3.2.3 下一条规定。\n继续描述。"
        ),
    )

    assert [segment.text for segment in segments] == [
        "上一条正文。",
        "3.2.2\n本条规定建筑结构应满足要求。",
        "3.2.3 下一条规定。\n继续描述。",
    ]


def test_decimal_in_natural_language_is_not_a_boundary() -> None:
    segments = LogicalLineSplitter().split(
        1,
        block("混凝土强度等级为 C30，长度为 3.2m。\n仍是同一段。"),
    )

    assert len(segments) == 1
    assert "3.2m" in segments[0].text


def test_split_preserves_effective_text_once() -> None:
    source = "上一段正文。\n\n3.2.2\n本条规定……\n9.1.3 板中钢筋……\n"
    segments = LogicalLineSplitter().split(2, block(source))

    reconstructed = "\n".join(segment.text for segment in segments)
    normalized = "\n".join(line.strip() for line in source.splitlines() if line.strip())
    assert reconstructed == normalized


def test_segments_keep_block_provenance_without_fake_line_boxes() -> None:
    source = block("正文。\n3.2.2 新条文。")
    segments = LogicalLineSplitter().split(8, source)

    assert [segment.segment_index for segment in segments] == [0, 1]
    assert all(segment.page_number == 8 for segment in segments)
    assert all(segment.source_block_number == 7 for segment in segments)
    assert all(segment.bbox == source.bbox for segment in segments)
