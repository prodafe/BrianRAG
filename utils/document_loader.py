import hashlib
import logging
import os
import re
import shutil
from collections.abc import Callable

from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_core.documents import Document

from config import Config

# ── Loader 插件注册表 ──
_loader_registry: dict[str, Callable[[str], list[Document]]] = {}


def register_loader(extensions: list[str]):
    """装饰器：注册自定义文档加载器。

    用法：
        @register_loader(['.custom', '.xyz'])
        def my_loader(file_path: str) -> List[Document]:
            return [Document(page_content=..., metadata=...)]
    """

    def decorator(func: Callable[[str], list[Document]]):
        for ext in extensions:
            _loader_registry[ext.lower()] = func
        return func

    return decorator


def get_registered_loaders() -> dict[str, str]:
    return {ext: fn.__name__ for ext, fn in _loader_registry.items()}


def _register_builtins():
    """注册内置加载器（在类定义之后调用）"""

    def _md(file_path):
        return MarkdownDocumentLoader().load(file_path)

    def _img(file_path):
        return _process_image_file(file_path)

    def _unified(file_path):
        return UnifiedDocumentLoader().load(file_path)

    def _text(file_path):
        """Plain text loader — read file as-is, split into chunks."""
        from langchain_core.documents import Document

        with open(file_path, encoding="utf-8", errors="replace") as f:
            content = f.read()
        if not content.strip():
            return []
        return [Document(page_content=content, metadata={"source": file_path, "type": "text"})]

    _loader_registry[".md"] = _md
    for e in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
        _loader_registry[e] = _img
    for e in [".pdf", ".docx", ".html", ".txt", ".csv", ".pptx", ".xlsx", ".xml", ".rtf", ".odt", ".epub", ".py"]:
        _loader_registry[e] = _unified
    # Plain-text / script / config formats: unstructured can't handle, use text loader
    for e in [".json", ".sh", ".rviz", ".ldenc", ".yml", ".yaml", ".toml", ".ini", ".cfg"]:
        _loader_registry[e] = _text


try:
    from unstructured.partition.auto import partition

    UNSTRUCTURED_AVAILABLE = True
except ImportError:
    UNSTRUCTURED_AVAILABLE = False
    logging.warning("unstructured 未安装，PDF/DOCX 等格式将无法解析")

logger = logging.getLogger(__name__)


def extract_image_paths(text: str) -> list:
    """从 Markdown 文本中提取所有图片 URL"""
    pattern = r"!\[.*?\]\((.*?)\)"
    return re.findall(pattern, text)


def get_file_hash(data: bytes) -> str:
    return hashlib.md5(data).hexdigest()


def _get_image_description(image_path: str) -> str | None:
    """可选的视觉模型描述，当前返回 None 以快速处理"""
    return None


def _process_image_file(file_path: str) -> list[Document]:
    """
    为单个图片文件生成 Document。
    - page_content 为文本描述（用于向量检索）
    - metadata 中包含 image_url（绝对URL）和 image_markdown（供 LLM 直接输出）
    """
    images_dir = Config.IMAGES_DIR
    os.makedirs(images_dir, exist_ok=True)

    # 哈希化文件名
    with open(file_path, "rb") as f:
        file_hash = get_file_hash(f.read())
    ext = os.path.splitext(file_path)[1].lower()
    if not ext:
        ext = ".img"
    new_filename = f"{file_hash}{ext}"
    dest_path = os.path.join(images_dir, new_filename)

    if not os.path.exists(dest_path):
        shutil.copy2(file_path, dest_path)
        logger.info(f"图片已复制到: {dest_path}")

    # 绝对 URL（后端静态服务）
    image_abs_url = f"http://localhost:8000/images/{new_filename}"
    # 描述文本：取文件名（不含扩展名）作为 alt
    alt_text = os.path.splitext(os.path.basename(file_path))[0]
    image_markdown = f"![{alt_text}]({image_abs_url})"

    # 文本描述（用于检索）
    text_description = _get_image_description(file_path)
    if not text_description:
        text_description = f"图片: {os.path.basename(file_path)}"

    # page_content 使用文本描述，避免检索结果直接是 Markdown 图片语法
    doc = Document(
        page_content=text_description,
        metadata={
            "source": file_path,
            "type": "image",
            "image_url": image_abs_url,
            "image_markdown": image_markdown,
            "original_filename": os.path.basename(file_path),
            "file_hash": file_hash,
            "alt_text": alt_text,
        },
    )
    return [doc]


def _split_markdown_by_sections(content: str, chunk_size: int = 500) -> list[str]:
    """按 Markdown 标题（##）拆分章节，保持图文关联。过长的章节再用 RecursiveCharacterTextSplitter 细分。"""
    # 按 ## 标题切割
    sections = re.split(r"\n(?=#{1,6}\s+)", content)
    result = []
    for section in sections:
        section = section.strip()
        if not section:
            continue
        if len(section) <= chunk_size:
            result.append(section)
        else:
            # 章节过长时，先尝试按 ### 子标题切分
            subs = re.split(r"\n(?=#{2,6}\s+)", section)
            for sub in subs:
                sub = sub.strip()
                if not sub:
                    continue
                if len(sub) <= chunk_size:
                    result.append(sub)
                else:
                    # 仍然过长，按段落切分
                    paragraphs = sub.split("\n\n")
                    current = ""
                    for para in paragraphs:
                        if len(current) + len(para) > chunk_size and current:
                            result.append(current.strip())
                            current = para
                        else:
                            current += ("\n\n" if current else "") + para
                    if current.strip():
                        result.append(current.strip())
    return result


def _enrich_image_only_chunk(chunk: str, prev_chunk: str = "", next_chunk: str = "") -> str:
    """如果 chunk 主要是图片引用，用前后文本来充实它"""
    # 提取所有非图片文本
    non_img_lines = [l for l in chunk.split("\n") if l.strip() and not l.strip().startswith("![")]
    non_img_text = " ".join(non_img_lines).strip()

    # 至少有 20 个非图片字符就不需要充实
    if len(non_img_text) >= 20:
        return chunk

    # 从前一个 chunk 取标题作为上下文
    enriched = chunk
    if prev_chunk:
        # 提取 prev 中的标题
        for line in prev_chunk.split("\n"):
            if line.startswith("#"):
                enriched = line.strip() + "\n\n" + enriched
                break
        # 如果没有标题，用前文的最后一句
        if enriched == chunk and len(prev_chunk) > 20:
            context = prev_chunk.strip()[-100:]
            enriched = context + "\n\n" + enriched

    return enriched


class MarkdownDocumentLoader:
    def __init__(self):
        self.image_dir = Config.IMAGES_DIR
        os.makedirs(self.image_dir, exist_ok=True)

    def load(self, file_path: str) -> list[Document]:
        with open(file_path, encoding="utf-8") as f:
            content = f.read()
        new_content = self._process_images(content, file_path)
        # 使用章节感知切分替代固定长度切分
        chunks = _split_markdown_by_sections(new_content, chunk_size=Config.CHUNK_SIZE)
        docs = []
        for i, chunk in enumerate(chunks):
            img_paths = extract_image_paths(chunk)
            # 用前后文充实纯图片 chunk
            prev_text = chunks[i - 1] if i > 0 else ""
            next_text = chunks[i + 1] if i + 1 < len(chunks) else ""
            enriched = _enrich_image_only_chunk(chunk, prev_text, next_text)
            docs.append(
                Document(page_content=enriched, metadata={"source": file_path, "type": "md", "images": img_paths})
            )
        return docs

    def _process_images(self, content: str, file_path: str) -> str:
        img_pattern = r"!\[(.*?)\]\((.*?)\)"
        base_dir = os.path.dirname(os.path.abspath(file_path))

        def replacer(match):
            alt = match.group(1)
            img_path = match.group(2).strip()

            if img_path.startswith(("http://", "https://")):
                try:
                    import requests

                    response = requests.get(img_path, timeout=10)
                    if response.status_code == 200:
                        img_data = response.content
                        content_type = response.headers.get("Content-Type", "")
                        if "png" in content_type:
                            ext = ".png"
                        elif "jpeg" in content_type or "jpg" in content_type:
                            ext = ".jpg"
                        else:
                            ext = ".img"
                        file_hash = get_file_hash(img_data)
                        filename = f"{file_hash}{ext}"
                        target_path = os.path.join(self.image_dir, filename)
                        if not os.path.exists(target_path):
                            with open(target_path, "wb") as f:
                                f.write(img_data)
                        url = f"http://localhost:8000/images/{filename}"
                        return f"![{alt}]({url})"
                    else:
                        logger.warning(f"网络图片下载失败: {img_path}")
                        return match.group(0)
                except Exception as e:
                    logger.error(f"下载网络图片异常: {e}")
                    return match.group(0)

            src = img_path if os.path.isabs(img_path) else os.path.normpath(os.path.join(base_dir, img_path))

            if not os.path.exists(src):
                logger.warning(f"图片不存在: {src}")
                return match.group(0)

            with open(src, "rb") as f:
                img_data = f.read()
            file_hash = get_file_hash(img_data)
            ext = os.path.splitext(src)[1]
            if not ext:
                ext = ".img"
            filename = f"{file_hash}{ext}"
            target_path = os.path.join(self.image_dir, filename)
            if not os.path.exists(target_path):
                shutil.copy2(src, target_path)
            url = f"http://localhost:8000/images/{filename}"
            return f"![{alt}]({url})"

        return re.sub(img_pattern, replacer, content)


class UnifiedDocumentLoader:
    def __init__(self):
        self.image_dir = Config.IMAGES_DIR
        os.makedirs(self.image_dir, exist_ok=True)

    def load(self, file_path: str) -> list[Document]:
        if not UNSTRUCTURED_AVAILABLE:
            logger.error("unstructured 未安装")
            return []

        try:
            elements = partition(
                filename=file_path, strategy="auto", include_page_breaks=False, languages=["chi_sim", "eng"]
            )
        except Exception:
            logger.warning(f"auto 策略失败，回退到 fast: {file_path}")
            elements = partition(
                filename=file_path, strategy="fast", include_page_breaks=False, languages=["chi_sim", "eng"]
            )

        markdown_parts = []
        for elem in elements:
            if elem.category == "Image":
                img_markdown = self._process_image_element(elem)
                if img_markdown:
                    markdown_parts.append(img_markdown)
            else:
                text = str(elem).strip()
                if text:
                    markdown_parts.append(text)

        full_markdown = "\n\n".join(markdown_parts)
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=Config.CHUNK_SIZE,
            chunk_overlap=Config.CHUNK_OVERLAP,
            separators=["\n\n", "\n", "。", "！", "？", "；", " ", ""],
        )
        chunks = splitter.split_text(full_markdown)

        docs = []
        for chunk in chunks:
            img_paths = extract_image_paths(chunk)
            docs.append(
                Document(
                    page_content=chunk, metadata={"source": file_path, "type": "unstructured", "images": img_paths}
                )
            )
        return docs

    def _process_image_element(self, elem) -> str:
        try:
            img_data = elem.metadata.image
            if not img_data:
                return ""
            img_type = elem.metadata.image_type or "png"
            if not img_type.startswith("."):
                img_type = f".{img_type}"
            file_hash = get_file_hash(img_data)
            filename = f"{file_hash}{img_type}"
            target_path = os.path.join(self.image_dir, filename)
            if not os.path.exists(target_path):
                with open(target_path, "wb") as f:
                    f.write(img_data)
            url = f"http://localhost:8000/images/{filename}"
            caption = "图片"
            return f"![{caption}]({url})"
        except Exception as e:
            logger.error(f"处理图片元素失败: {e}")
            return ""


def load_single_document(file_path: str) -> list[Document]:
    ext = os.path.splitext(file_path)[1].lower()

    # PDF：优先用版式分析器（大文件直接用 PyMuPDF 避免超时）
    if ext == ".pdf":
        if os.path.getsize(file_path) > 20 * 1024 * 1024:
            size_mb = os.path.getsize(file_path) // 1024 // 1024
            logger.info(f"PDF 过大 ({size_mb}MB)，使用 PyMuPDF 快速提取: {file_path}")
            try:
                import fitz
                from langchain_core.documents import Document

                docs = []
                doc = fitz.open(file_path)
                current_chunk = ""
                for page in doc:
                    page_text = page.get_text().strip()
                    if not page_text:
                        continue
                    if len(current_chunk) + len(page_text) < Config.CHUNK_SIZE * 4:
                        current_chunk += "\n\n" + page_text
                    else:
                        if current_chunk.strip():
                            docs.append(Document(page_content=current_chunk.strip(),
                                                 metadata={"source": file_path, "type": "pdf_pymupdf"}))
                        current_chunk = page_text
                if current_chunk.strip():
                    docs.append(Document(page_content=current_chunk.strip(),
                                         metadata={"source": file_path, "type": "pdf_pymupdf"}))
                doc.close()
                if docs:
                    return docs
            except Exception as e:
                logger.warning(f"PyMuPDF 提取失败: {e}")
            return []
        else:
            try:
                from utils.layout_analyzer import analyze_pdf_layout, pdf_has_text_layer

                if pdf_has_text_layer(file_path):
                    logger.info(f"使用版式分析器处理: {file_path}")
                    md_text = analyze_pdf_layout(file_path, image_output_dir=Config.IMAGES_DIR)
                    if md_text and len(md_text) > 100:
                        splitter = RecursiveCharacterTextSplitter(
                            chunk_size=getattr(Config, "chunk_size", 800),
                            chunk_overlap=getattr(Config, "chunk_overlap", 100),
                            separators=["\n\n", "\n", "。", ". ", " ", ""],
                        )
                        chunks = splitter.split_text(md_text)
                        docs = [
                            Document(page_content=chunk, metadata={"source": file_path, "type": "pdf_layout_analyzed"})
                            for chunk in chunks
                        ]
                        _apply_ocr_to_docs(docs, file_path, is_image=False)
                        return docs
                    logger.info(f"版式分析器输出不足，回退: {file_path}")
            except ImportError:
                pass
            except Exception as e:
                logger.warning(f"版式分析失败: {e}")

    # 图片：OCR 补充
    if ext in [".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp"]:
        docs = _process_image_file(file_path)
        _apply_ocr_to_docs(docs, file_path, is_image=True)
        return docs

    # 通过注册表分发（支持用户自定义 loader）
    if ext in _loader_registry:
        docs = _loader_registry[ext](file_path)
        if ext == ".pdf":
            _apply_ocr_to_docs(docs, file_path, is_image=False)
        return docs

    # 回退：统一加载器
    logger.info(f"未注册扩展名 {ext}，回退到 unstructured")
    loader = UnifiedDocumentLoader()
    return loader.load(file_path)


def _apply_ocr_to_docs(docs: list[Document], file_path: str, is_image: bool = False):
    """对文档补充 OCR 文字"""
    try:
        from utils.ocr import extract_text_from_image, extract_text_from_pdf, is_scanned_pdf

        if is_image:
            ocr_text = extract_text_from_image(file_path)
        elif file_path.lower().endswith(".pdf") and is_scanned_pdf(file_path):
            ocr_text = extract_text_from_pdf(file_path)
        else:
            return
        if ocr_text and len(ocr_text) > 10:
            for doc in docs:
                doc.page_content = f"{doc.page_content}\n[OCR文字]\n{ocr_text}"
            logger.info(f"OCR 文字已补充: {file_path} ({len(ocr_text)} 字符)")
    except ImportError:
        pass
    except Exception as e:
        logger.warning(f"OCR 补充失败: {e}")


# 初始化内置加载器注册表
_register_builtins()
