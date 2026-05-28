"""TOC 提取 + 数据源连接器测试"""

import pytest


class TestTOCExtraction:
    def test_markdown_toc(self):
        from utils.data_connectors import extract_toc_from_markdown

        md = "# Title\n## Section 1\nSome text\n### Sub 1.1\nMore\n## Section 2\nText"
        toc = extract_toc_from_markdown(md)
        assert len(toc) >= 1
        assert toc[0]["title"] == "Title"
        assert toc[0]["level"] == 1

    def test_markdown_toc_depth_limit(self):
        from utils.data_connectors import extract_toc_from_markdown

        md = "# H1\n## H2\n### H3\n#### H4"
        toc = extract_toc_from_markdown(md, max_depth=2)
        for item in toc:
            assert item["level"] <= 2

    def test_empty_content(self):
        from utils.data_connectors import extract_toc_from_markdown

        assert extract_toc_from_markdown("") == []

    def test_toc_tree_string(self):
        from utils.data_connectors import extract_toc_from_markdown, toc_to_tree_string

        md = "# Root\n## Child1\n### Grandchild"
        toc = extract_toc_from_markdown(md)
        tree = toc_to_tree_string(toc)
        assert "Root" in tree
        assert "Child1" in tree

    def test_extract_toc_pdf_missing(self):
        from utils.data_connectors import extract_toc_from_pdf

        result = extract_toc_from_pdf("/nonexistent/file.pdf")
        assert result == []

    def test_auto_extract_toc_md(self):
        from utils.data_connectors import auto_extract_toc
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", encoding="utf-8", delete=False) as f:
            f.write("# Doc Title\n## Intro\nContent here\n## Details\nMore content")
            tmp = f.name

        try:
            toc = auto_extract_toc(tmp)
            assert len(toc) >= 1
            assert toc[0]["title"] == "Doc Title"
        finally:
            os.unlink(tmp)


class TestNotionConnector:
    def test_initialization(self):
        from utils.data_connectors import NotionConnector

        conn = NotionConnector(api_key="test_key")
        assert conn.api_key == "test_key"
        assert "notion" in conn.base_url.lower()


class TestS3Connector:
    def test_initialization(self):
        from utils.data_connectors import S3Connector

        conn = S3Connector(bucket="my-bucket", access_key="AKID", secret_key="secret")
        assert conn.bucket == "my-bucket"

    def test_no_client_without_boto3(self, monkeypatch):
        monkeypatch.setattr("utils.data_connectors.S3Connector.client", property(lambda s: None))
        from utils.data_connectors import S3Connector

        conn = S3Connector()
        files = conn.list_files()
        assert files == []
