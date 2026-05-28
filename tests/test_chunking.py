"""父子分块 + Table-aware 切分测试"""

from langchain_core.documents import Document


class TestTableDetection:
    def test_markdown_table_detected(self):
        from core.chunking import _detect_tables

        text = "Some text\n| Header1 | Header2 |\n|---------|---------|\n| val1    | val2    |\nMore text"
        tables = _detect_tables(text)
        assert len(tables) >= 1

    def test_no_table(self):
        from core.chunking import _detect_tables

        text = "Just plain text\nNo tables here.\nAnother line."
        tables = _detect_tables(text)
        assert len(tables) == 0


class TestTableAwareSplit:
    def test_table_preserved(self):
        from core.chunking import _table_aware_split

        text = "Intro.\n\n| A | B |\n|---|---|\n| 1 | 2 |\n\nOutro."
        chunks = _table_aware_split(text, chunk_size=100)
        # Table should be in its own chunk
        table_chunks = [c for c in chunks if "|" in c]
        assert len(table_chunks) >= 1
        # Table should not be split
        for tc in table_chunks:
            assert "| A |" in tc
            assert "| 1 |" in tc

    def test_no_table_normal_split(self):
        from core.chunking import _table_aware_split

        text = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5\nLine 6\nLine 7\nLine 8"
        chunks = _table_aware_split(text, chunk_size=20)
        assert len(chunks) > 1


class TestParentChildChunk:
    def test_generates_both_types(self):
        from core.chunking import parent_child_chunk

        doc = Document(page_content="Paragraph one.\n\nParagraph two.\n\nParagraph three.\n\n" * 10,
                       metadata={"source": "test.md"})
        children, parents = parent_child_chunk([doc], child_size=200, child_overlap=50, parent_window=3)

        assert len(children) > 0
        assert len(parents) > 0
        assert all(c.metadata.get("chunk_type") == "child" for c in children)
        assert all(p.metadata.get("chunk_type") == "parent" for p in parents)

    def test_parent_larger_than_child(self):
        from core.chunking import parent_child_chunk

        text = ("Section A content here. " * 20 + "\n\n" +
                "Section B content here. " * 20 + "\n\n" +
                "Section C content here. " * 20)
        doc = Document(page_content=text, metadata={"source": "test.md"})
        children, parents = parent_child_chunk([doc], child_size=100, child_overlap=20, parent_window=4)

        if parents:
            avg_child_len = sum(len(c.page_content) for c in children) / len(children) if children else 0
            avg_parent_len = sum(len(p.page_content) for p in parents) / len(parents) if parents else 0
            assert avg_parent_len > avg_child_len
