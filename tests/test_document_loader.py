"""文档加载器模块测试"""

import os
import tempfile


class TestLoadSingleDocument:
    def test_missing_file_returns_empty(self):
        from utils.document_loader import load_single_document
        docs = load_single_document("/nonexistent/file.md")
        assert docs == []

    def test_md_file_loaded(self):
        from utils.document_loader import _register_builtins, load_single_document

        _register_builtins()
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", encoding="utf-8", delete=False) as f:
            f.write("# Test\n\nHello world.\n\n## Section 2\n\nMore content here.")
            tmp_path = f.name

        try:
            docs = load_single_document(tmp_path)
            assert len(docs) > 0
            assert any("Hello world" in d.page_content for d in docs)
        finally:
            os.unlink(tmp_path)

    def test_image_file_generates_image_doc(self):
        from utils.document_loader import _register_builtins, load_single_document

        _register_builtins()
        from PIL import Image

        img = Image.new("RGB", (100, 100), color="red")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f.name)
            tmp_path = f.name

        try:
            docs = load_single_document(tmp_path)
            assert len(docs) > 0
            assert docs[0].metadata.get("type") == "image"
            assert "image_url" in docs[0].metadata
        finally:
            os.unlink(tmp_path)

    def test_no_read_permission_returns_empty(self, monkeypatch):
        monkeypatch.setattr(os.path, "isfile", lambda p: True)
        monkeypatch.setattr(os, "access", lambda p, m: False)
        from utils.document_loader import load_single_document

        docs = load_single_document("/some/protected/file.md")
        assert docs == []


class TestMarkdownDocumentLoader:
    def test_basic_load(self):
        from utils.document_loader import MarkdownDocumentLoader

        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", encoding="utf-8", delete=False) as f:
            f.write("# Title\n\nParagraph one.\n\n## Sub\n\nParagraph two with more text content for testing.")
            tmp_path = f.name

        try:
            loader = MarkdownDocumentLoader()
            docs = loader.load(tmp_path)
            assert len(docs) > 0
            for doc in docs:
                assert doc.metadata.get("source") == tmp_path
                assert doc.metadata.get("type") == "md"
        finally:
            os.unlink(tmp_path)

    def test_image_path_extraction(self):
        from utils.document_loader import extract_image_paths

        text = "Some text ![alt](image.png) more text ![alt2](/path/to/img.jpg)"
        paths = extract_image_paths(text)
        assert len(paths) == 2
        assert "image.png" in paths
        assert "/path/to/img.jpg" in paths

    def test_no_images_in_text(self):
        from utils.document_loader import extract_image_paths

        assert extract_image_paths("Plain text without images") == []


class TestGetFileHash:
    def test_hash_consistency(self):
        from utils.document_loader import get_file_hash

        data = b"test data for hashing"
        h1 = get_file_hash(data)
        h2 = get_file_hash(data)
        assert h1 == h2
        assert len(h1) == 32

    def test_different_data_different_hash(self):
        from utils.document_loader import get_file_hash

        assert get_file_hash(b"abc") != get_file_hash(b"abd")


class TestLoaderRegistry:
    def test_builtin_registry_populated(self):
        from utils.document_loader import _loader_registry, _register_builtins

        _register_builtins()
        assert ".md" in _loader_registry
        assert ".pdf" in _loader_registry
        assert ".jpg" in _loader_registry
        assert ".png" in _loader_registry

    def test_custom_loader_registration(self):
        from langchain_core.documents import Document

        from utils.document_loader import _loader_registry, register_loader

        @register_loader([".custom"])
        def custom_loader(file_path: str):
            return [Document(page_content="custom", metadata={"source": file_path})]

        assert ".custom" in _loader_registry
        docs = _loader_registry[".custom"]("/fake/file.custom")
        assert len(docs) == 1
        assert docs[0].page_content == "custom"

    def test_get_registered_loaders(self):
        from utils.document_loader import _register_builtins, get_registered_loaders

        _register_builtins()
        loaders = get_registered_loaders()
        assert isinstance(loaders, dict)
        assert len(loaders) > 0
