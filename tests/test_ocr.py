"""OCR 模块测试"""

import pytest


class TestOCREngineStatus:
    def test_ocr_status_returns_dict(self):
        from utils.ocr import ocr_status

        status = ocr_status()
        assert isinstance(status, dict)
        assert "engine" in status
        assert "tesseract_available" in status
        assert "paddle_available" in status
        assert status["engine"] in ("paddle", "tesseract", "none")

    def test_extract_text_missing_file(self):
        from utils.ocr import extract_text_from_image

        result = extract_text_from_image("/nonexistent/image.png")
        assert result == ""


class TestScannedPDF:
    def test_is_scanned_pdf_missing_file(self):
        from utils.ocr import is_scanned_pdf

        assert is_scanned_pdf("/nonexistent/file.pdf") is False


class TestOCRResize:
    def test_resize_small_image_noop(self):
        from utils.ocr import _resize_for_ocr

        from PIL import Image
        import tempfile
        import os

        img = Image.new("RGB", (100, 100), color="white")
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as f:
            img.save(f.name)
            tmp = f.name

        try:
            result = _resize_for_ocr(tmp, max_side=2000)
            assert result == tmp
        finally:
            os.unlink(tmp)

    def test_resize_large_image(self):
        from utils.ocr import _resize_for_ocr

        from PIL import Image
        import tempfile
        import os

        img = Image.new("RGB", (3000, 3000), color="white")
        tmp = tempfile.mktemp(suffix=".png")
        img.save(tmp)

        try:
            result = _resize_for_ocr(tmp, max_side=2000)
            assert result != tmp
            assert os.path.exists(result)
            from PIL import Image as PILImage

            resized = PILImage.open(result)
            resized.load()
            assert max(resized.size) == 2000
            resized.close()
            os.unlink(result)
        finally:
            os.unlink(tmp)

    def test_resize_invalid_image(self):
        from utils.ocr import _resize_for_ocr

        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".txt", mode="w", delete=False) as f:
            f.write("not an image")
            tmp = f.name

        try:
            result = _resize_for_ocr(tmp)
            assert result is None
        finally:
            os.unlink(tmp)


class TestExtractTextFromPDF:
    def test_missing_file(self):
        from utils.ocr import extract_text_from_pdf

        result = extract_text_from_pdf("/nonexistent/doc.pdf")
        assert result == ""
