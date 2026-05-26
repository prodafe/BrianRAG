"""OCR 模块 — 扫描件 PDF/图片文字提取，支持 Tesseract 和 PaddleOCR"""
import logging
import os
import tempfile
from typing import Optional

import numpy as np
from PIL import Image

from config import Config

logger = logging.getLogger(__name__)

# 检测可用的 OCR 引擎
_TESSERACT_OK = False
_PADDLE_OK = False

try:
    import pytesseract  # noqa: F401

    _TESSERACT_OK = True
except ImportError:
    pass

try:
    from paddleocr import PaddleOCR  # noqa: F401

    _PADDLE_OK = True
except ImportError:
    pass

_ocr_instance: Optional[object] = None


def _get_paddle():
    global _ocr_instance
    if _ocr_instance is None:
        try:
            from paddleocr import PaddleOCR

            _ocr_instance = PaddleOCR(lang="ch", use_angle_cls=True, show_log=False)
        except Exception as e:
            logger.warning(f"PaddleOCR 初始化失败: {e}")
            _ocr_instance = False
    return _ocr_instance if _ocr_instance is not False else None


def extract_text_from_image(image_path: str, engine: str = "auto") -> str:
    """从单张图片提取文字。engine: auto/paddle/tesseract"""
    if not os.path.exists(image_path):
        return ""

    if engine == "auto":
        if _PADDLE_OK:
            engine = "paddle"
        elif _TESSERACT_OK:
            engine = "tesseract"
        else:
            logger.warning("未安装任何 OCR 引擎，跳过图片文字提取")
            return ""

    if engine == "paddle":
        return _ocr_paddle(image_path)
    elif engine == "tesseract":
        return _ocr_tesseract(image_path)
    return ""


def _ocr_tesseract(image_path: str) -> str:
    try:
        import pytesseract

        img = Image.open(image_path).convert("RGB")
        text = pytesseract.image_to_string(img, lang="chi_sim+eng")
        return text.strip()
    except Exception as e:
        logger.error(f"Tesseract OCR 失败: {e}")
        return ""


def _ocr_paddle(image_path: str) -> str:
    try:
        ocr = _get_paddle()
        if not ocr:
            return ""
        result = ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            return ""
        lines = []
        for line in result[0]:
            if line and len(line) >= 2:
                text = line[1][0]
                confidence = line[1][1]
                if confidence > 0.5:
                    lines.append(text)
        return "\n".join(lines)
    except Exception as e:
        logger.error(f"PaddleOCR 失败: {e}")
        return ""


def extract_text_from_pdf(pdf_path: str, engine: str = "auto") -> str:
    """从 PDF 提取文字。文字型 PDF 用 PyMuPDF，扫描件用 OCR"""
    try:
        import fitz  # PyMuPDF

        doc = fitz.open(pdf_path)
        text_parts = []
        for page_num in range(len(doc)):
            page = doc[page_num]
            text = page.get_text()
            if text.strip():
                text_parts.append(text.strip())
            else:
                # 无文字层 → OCR 扫描页
                pix = page.get_pixmap(dpi=200)
                with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
                    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                    img.save(tmp.name)
                    ocr_text = extract_text_from_image(tmp.name, engine=engine)
                    if ocr_text:
                        text_parts.append(ocr_text)
                    os.unlink(tmp.name)
        doc.close()
        return "\n\n".join(text_parts)
    except ImportError:
        logger.warning("PyMuPDF 未安装，无法解析PDF")
        return ""
    except Exception as e:
        logger.error(f"PDF 解析失败: {e}")
        return ""


def is_scanned_pdf(pdf_path: str) -> bool:
    """判断 PDF 是否主要为扫描件（文字层为空或极少）"""
    try:
        import fitz

        doc = fitz.open(pdf_path)
        total_chars = 0
        for page in doc:
            total_chars += len(page.get_text().strip())
        doc.close()
        pages = max(len(doc), 1)
        return (total_chars / pages) < 20
    except Exception:
        return False


def ocr_status() -> dict:
    """返回 OCR 引擎状态"""
    return {
        "tesseract_available": _TESSERACT_OK,
        "paddle_available": _PADDLE_OK,
        "engine": "paddle" if _PADDLE_OK else "tesseract" if _TESSERACT_OK else "none",
    }
