from engineering_rag.chunking import EngineeringChunker
from engineering_rag.ingestion.parser import Document, Page, TextBlock
from engineering_rag.ingestion.structure import StructureParser, StructureRole


def make_document(*pages: list[tuple[str, float]]) -> Document:
    return Document(
        document_id="state-test",
        source_file="state-test.pdf",
        page_count=len(pages),
        pages=[
            Page(
                page_number=page_number,
                text="\n".join(text for text, _ in page),
                blocks=[
                    TextBlock(
                        text=text,
                        bbox=[10.0, y, 500.0, y + 12.0],
                        block_number=index,
                        block_type=0,
                    )
                    for index, (text, y) in enumerate(page)
                ],
            )
            for page_number, page in enumerate(pages, start=1)
        ],
    )


def test_explanation_mode_survives_chapters_sections_and_pages() -> None:
    document = make_document(
        [("条文说明", 100), ("3 基本设计规定", 130), ("3.1 一般规定", 160)],
        [("3.1.1 本条说明内容。", 100), ("4 第二章说明", 130)],
        [("4.1.1 第二章条文说明。", 100)],
    )

    structure = StructureParser().parse(document)

    assert all(block.is_explanation for block in structure.blocks)
    assert structure.blocks[1].role == StructureRole.CHAPTER
    assert structure.blocks[2].role == StructureRole.SECTION
    assert structure.blocks[3].role == StructureRole.CLAUSE
    assert structure.blocks[5].role == StructureRole.CLAUSE


def test_same_clause_number_in_body_and_explanation_produces_separate_chunks() -> None:
    document = make_document(
        [("4.2.3 正文要求。", 100), ("条文说明", 140), ("4 基本规定", 180)],
        [("4.2 一般规定", 100), ("4.2.3 本条说明。", 140)],
    )

    chunks = EngineeringChunker().chunk(StructureParser().parse(document))
    matching = [chunk for chunk in chunks if chunk.clause_number == "4.2.3"]

    assert len(matching) == 2
    assert {chunk.is_explanation for chunk in matching} == {False, True}
    assert len({chunk.logical_chunk_id for chunk in matching}) == 2


def test_sentence_containing_phrase_does_not_enter_explanation_mode() -> None:
    structure = StructureParser().parse(
        make_document([("本段介绍条文说明的编写方法。", 100), ("3.1.1 正文。", 130)])
    )

    assert not any(block.is_explanation for block in structure.blocks)


def test_explicit_semantic_boundary_can_exit_explanation_mode() -> None:
    structure = StructureParser().parse(
        make_document(
            [("条文说明", 100), ("3.1.1 说明。", 130), ("本规范用词说明", 160), ("正文。", 190)]
        )
    )

    assert structure.blocks[1].is_explanation is True
    assert structure.blocks[2].is_explanation is False
    assert structure.blocks[3].is_explanation is False
    chunks = EngineeringChunker().chunk(structure)
    assert chunks[-1].is_explanation is False


def test_repeated_margin_text_cannot_change_explanation_mode() -> None:
    document = make_document(
        [("条文说明", 10), ("1 正文章", 100)],
        [("条文说明", 10), ("1.1.1 正文条文。", 100)],
    )

    structure = StructureParser().parse(document)

    assert structure.blocks[0].role == StructureRole.HEADER
    assert structure.blocks[2].role == StructureRole.HEADER
    assert structure.blocks[1].is_explanation is False
    assert structure.blocks[3].is_explanation is False
