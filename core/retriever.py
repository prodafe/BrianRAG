import asyncio
import sys

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
import hashlib
import json
import logging
import os
import pickle
import re
import time
from concurrent.futures import ThreadPoolExecutor

import jieba
import jieba.analyse
import numpy as np
import ollama
import torch
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_postgres import PGEngine, PGVectorStore
from PIL import Image
from rank_bm25 import BM25Okapi
from sqlalchemy import create_engine, text
from transformers import CLIPModel, CLIPProcessor

from config import Config
from core.intent_classifier import IntentClassifier

# METRICS: 导入指标记录函数
from core.metrics import record_retrieval, record_vision_call
from utils.document_loader import load_single_document

logger = logging.getLogger(__name__)

# Module-level shared cache: avoids reloading chunks for each HybridRetriever instance
_shared = {
    "chunks": None,
    "chunk_metadata": None,
    "chunk_images": None,
    "bm25": None,
    "doc_meta": None,
    "graph_builder": None,
}


class OllamaEmbeddings(Embeddings):
    def __init__(self, model: str, dim: int):
        self.model = model
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            response = ollama.embed(model=self.model, input=texts)
            return response["embeddings"]
        except Exception as e:
            logger.error(f"Ollama 嵌入失败: {e}")
            return [[0.0] * self.dim for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]


# ── CLIP 多模态检索器 ─────────────────────────────────────


class ClipRetriever:
    def __init__(self, model_path: str | None = None, index_path: str | None = None):
        self.model_path = model_path or getattr(Config, "MULTIMODAL_MODEL_PATH", r"D:\models\clip-ViT-B-32")
        self.index_path = index_path or os.path.join(Config.INDEX_DIR, "clip_index.pkl")
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        self.model = CLIPModel.from_pretrained(self.model_path).to(self.device)
        self.processor = CLIPProcessor.from_pretrained(self.model_path)
        self.model.eval()
        self.image_paths: list[str] = []
        self.image_metadatas: list[dict] = []
        self.image_embeddings: np.ndarray = np.empty((0, 512))
        self.load_index()

    def _to_abs_path(self, path: str) -> str:
        if os.path.isabs(path):
            return path
        return os.path.join(Config.DATA_DIR, path)

    def _encode_text(self, texts: list[str]) -> np.ndarray:
        inputs = self.processor(text=texts, return_tensors="pt", padding=True, truncation=True).to(self.device)
        with torch.no_grad():
            embeddings = self.model.get_text_features(**inputs)
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
        return embeddings.cpu().numpy()

    def _encode_image(self, image_paths: list[str]) -> tuple[np.ndarray, list[int]]:
        pil_images = []
        valid_indices = []
        for i, path in enumerate(image_paths):
            abs_path = self._to_abs_path(path)
            if os.path.exists(abs_path):
                try:
                    img = Image.open(abs_path).convert("RGB")
                    pil_images.append(img)
                    valid_indices.append(i)
                except Exception as e:
                    logger.warning(f"无法加载图片 {abs_path}: {e}")
        if not pil_images:
            return np.empty((0, 512)), []
        inputs = self.processor(images=pil_images, return_tensors="pt").to(self.device)
        with torch.no_grad():
            embeddings = self.model.get_image_features(**inputs)
        embeddings = embeddings / embeddings.norm(dim=-1, keepdim=True)
        return embeddings.cpu().numpy(), valid_indices

    def rebuild_index_from_documents(self, documents: list[Document]):
        image_paths = []
        metadatas = []
        for doc in documents:
            img_path = doc.metadata.get("image_path") or doc.metadata.get("source")
            if img_path:
                abs_path = self._to_abs_path(img_path)
                if os.path.exists(abs_path):
                    image_paths.append(abs_path)
                    metadatas.append(doc.metadata)
        if not image_paths:
            logger.warning("没有有效的图片路径，索引为空")
            self.image_paths = []
            self.image_metadatas = []
            self.image_embeddings = np.empty((0, 512))
            self.save_index()
            return
        embeddings, valid_indices = self._encode_image(image_paths)
        self.image_paths = [image_paths[i] for i in valid_indices]
        self.image_metadatas = [metadatas[i] for i in valid_indices]
        self.image_embeddings = embeddings
        logger.info(f"多模态索引重建完成，共 {len(self.image_paths)} 张图片")
        self.save_index()

    def add_image(self, image_path: str, metadata: dict = None):
        abs_path = self._to_abs_path(image_path)
        if not os.path.exists(abs_path):
            logger.warning(f"图片不存在: {abs_path}")
            return
        if abs_path in self.image_paths:
            return
        embeddings, valid = self._encode_image([abs_path])
        if len(valid) == 0:
            return
        self.image_paths.append(abs_path)
        self.image_metadatas.append(metadata or {})
        if self.image_embeddings.size == 0:
            self.image_embeddings = embeddings
        else:
            self.image_embeddings = np.vstack([self.image_embeddings, embeddings])

    def remove_image(self, image_path: str):
        abs_path = self._to_abs_path(image_path)
        if abs_path in self.image_paths:
            idx = self.image_paths.index(abs_path)
            del self.image_paths[idx]
            del self.image_metadatas[idx]
            self.image_embeddings = np.delete(self.image_embeddings, idx, axis=0)
            logger.info(f"已删除图片: {abs_path}")

    def save_index(self):
        os.makedirs(os.path.dirname(self.index_path), exist_ok=True)
        data = {
            "image_paths": self.image_paths,
            "image_metadatas": self.image_metadatas,
            "image_embeddings": self.image_embeddings,
        }
        with open(self.index_path, "wb") as f:
            pickle.dump(data, f)
        logger.info(f"多模态索引已保存至 {self.index_path}")

    def load_index(self):
        if not os.path.exists(self.index_path):
            logger.info("未找到已有的多模态索引文件，将从头构建")
            return
        try:
            with open(self.index_path, "rb") as f:
                data = pickle.load(f)
            self.image_paths = data["image_paths"]
            self.image_metadatas = data["image_metadatas"]
            self.image_embeddings = data["image_embeddings"]
            logger.info(f"已加载多模态索引，共 {len(self.image_paths)} 张图片")
        except Exception as e:
            logger.error(f"加载多模态索引失败: {e}")

    def search_by_text(self, query: str, top_k: int = 3) -> list[tuple[dict, float]]:
        if self.image_embeddings.size == 0:
            return []
        query_emb = self._encode_text([query])
        scores = np.dot(self.image_embeddings, query_emb.T).flatten()
        top_indices = np.argsort(scores)[-top_k:][::-1]
        results = []
        for idx in top_indices:
            if scores[idx] > 0.1:
                results.append((self.image_metadatas[idx], float(scores[idx])))
        return results


# ── 智能分块 ──────────────────────────────────────────────

_MIN_CHUNK_LEN = 50  # 短于此值的 chunk 会被合并到相邻 chunk


def _semantic_chunk_paragraphs(paragraphs: list[str], threshold: float = 0.45) -> list[str]:
    """用 bge-m3 嵌入相似度检测话题边界，将段落聚合成语义连贯的 chunk。
    相邻段落间余弦相似度低于 threshold 的点视为边界。"""
    if len(paragraphs) <= 1:
        return paragraphs
    try:
        import ollama

        from config import Config

        resp = ollama.embed(model=Config.EMBEDDING_MODEL, input=paragraphs)
        embeddings = resp["embeddings"]
    except Exception:
        return paragraphs  # 嵌入失败时回退

    import numpy as np

    # 计算相邻段落相似度
    similarities = []
    for i in range(len(embeddings) - 1):
        a = np.array(embeddings[i], dtype=np.float32)
        b = np.array(embeddings[i + 1], dtype=np.float32)
        sim = np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-8)
        similarities.append(sim)

    # 找到相似度低于阈值的索引作为边界
    boundaries = [i + 1 for i, s in enumerate(similarities) if s < threshold]

    if not boundaries:
        return ["\n\n".join(paragraphs)]

    # 按边界聚合
    result = []
    start = 0
    for boundary in boundaries:
        chunk = "\n\n".join(paragraphs[start:boundary])
        if chunk.strip():
            result.append(chunk.strip())
        start = boundary
    # 最后一个
    chunk = "\n\n".join(paragraphs[start:])
    if chunk.strip():
        result.append(chunk.strip())
    return result


def _merge_short_chunks(chunks: list[Document]) -> list[Document]:
    """将过短的 chunk 与相邻 chunk 合并，避免图片引用等孤立碎片"""
    if len(chunks) <= 1:
        return chunks
    merged = []
    i = 0
    while i < len(chunks):
        doc = chunks[i]
        text = doc.page_content
        # 表和数据类 chunk 不合并
        if doc.metadata.get("type") in ("table", "table_raw"):
            merged.append(doc)
            i += 1
            continue
        if len(text) >= _MIN_CHUNK_LEN:
            merged.append(doc)
            i += 1
            continue
        # 太短 → 尝试向前或向后合并
        if len(merged) > 0 and merged[-1].metadata.get("type") not in ("table", "table_raw"):
            # 向前合并
            prev = merged[-1]
            prev.page_content = prev.page_content + "\n\n" + text
            if doc.metadata.get("images"):
                prev_imgs = prev.metadata.get("images", [])
                prev.metadata["images"] = prev_imgs + doc.metadata.get("images", [])
            i += 1
        elif i + 1 < len(chunks):
            # 向后合并
            next_doc = chunks[i + 1]
            next_doc.page_content = text + "\n\n" + next_doc.page_content
            if doc.metadata.get("images"):
                next_imgs = next_doc.metadata.get("images", [])
                next_doc.metadata["images"] = doc.metadata.get("images", []) + next_imgs
            i += 1
        else:
            merged.append(doc)
            i += 1
    return merged


def smart_split_markdown(documents: list[Document], chunk_size: int = 1000, chunk_overlap: int = 200) -> list[Document]:
    final_chunks = []
    current_section = "Root"
    for doc in documents:
        content = doc.page_content
        lines = content.split("\n")
        for line in lines:
            if line.startswith("#"):
                current_section = line.lstrip("#").strip()
                break
        if doc.metadata.get("type") in ("table", "table_raw", "image_desc"):
            new_meta = doc.metadata.copy()
            new_meta["section"] = current_section
            final_chunks.append(Document(page_content=doc.page_content, metadata=new_meta))
            continue
        sections = re.split(r"\n(?=#{1,6}\s+)", content)
        if len(sections) == 1:
            sections = re.split(r"\n\s*\n", content)

        # 语义分块：对过长的 section 用嵌入相似度找话题边界
        use_semantic = getattr(Config, "ENABLE_SEMANTIC_CHUNKING", False)
        sem_threshold = getattr(Config, "SEMANTIC_CHUNK_THRESHOLD", 0.45)
        expanded_sections = []
        for sec in sections:
            sec = sec.strip()
            if not sec:
                continue
            if use_semantic and len(sec) > chunk_size:
                paragraphs = [p.strip() for p in sec.split("\n\n") if p.strip()]
                if len(paragraphs) >= 3:
                    sub_chunks = _semantic_chunk_paragraphs(paragraphs, threshold=sem_threshold)
                    expanded_sections.extend(sub_chunks)
                    continue
            expanded_sections.append(sec)
        sections = expanded_sections

        current_chunk = ""
        for section in sections:
            if not section.strip():
                continue
            if len(current_chunk) + len(section) > chunk_size and current_chunk:
                new_meta = doc.metadata.copy()
                new_meta["section"] = current_section
                final_chunks.append(Document(page_content=current_chunk.strip(), metadata=new_meta))
                overlap = (
                    current_chunk[-chunk_overlap:] if chunk_overlap > 0 and len(current_chunk) > chunk_overlap else ""
                )
                current_chunk = overlap + "\n\n" + section if overlap else section
            else:
                current_chunk += ("\n\n" if current_chunk else "") + section
        if current_chunk:
            new_meta = doc.metadata.copy()
            new_meta["section"] = current_section
            final_chunks.append(Document(page_content=current_chunk.strip(), metadata=new_meta))
    return _merge_short_chunks(final_chunks)


class HybridRetriever:
    def __init__(self):
        self.dim = Config.EMBEDDING_DIM
        self.chunks = []
        self.chunk_metadata = []
        self.chunk_images = []
        self.bm25 = None
        self.is_loaded = False
        self._synced_from_db = False
        self.doc_meta = {}
        self.graph_builder = None
        self.chunks_data_path = os.path.join(Config.INDEX_DIR, "chunks_data.pkl")

        self.intent_classifier = IntentClassifier()
        self._load_doc_meta()

        # 数据库初始化
        self._init_success = False
        try:
            sync_db_url = Config.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
            self.db_engine = create_engine(sync_db_url, pool_size=10, max_overflow=20, pool_pre_ping=True, echo=False)
            self.pg_engine = PGEngine.from_connection_string(url=sync_db_url)
            self.table_name = "brianrag_vectors"
            self.pg_engine.init_vectorstore_table(
                table_name=self.table_name, vector_size=self.dim, overwrite_existing=True
            )
            embedding = OllamaEmbeddings(Config.EMBEDDING_MODEL, self.dim)
            self.vector_store = PGVectorStore.create_sync(
                engine=self.pg_engine,
                table_name=self.table_name,
                embedding_service=embedding,
            )
            try:
                with self.db_engine.connect() as conn:
                    conn.execute(text(f"SET hnsw.ef_search = {Config.VECTOR_HNSW_EF_SEARCH}"))
                    conn.commit()
            except Exception as e:
                logger.debug(f"HNSW index creation skipped: {e}")
            self._init_success = True
            logger.info("HybridRetriever 初始化成功（向量存储就绪）")
        except Exception as e:
            logger.error(f"HybridRetriever 初始化失败: {e}", exc_info=True)
            self.pg_engine = None
            self.vector_store = None
            self.db_engine = None
            self._init_success = False

        # 多模态检索器（懒加载 + 健壮降级）
        self._clip_retriever = None
        self._multimodal_available = False
        if Config.ENABLE_MULTIMODAL and self._init_success:
            logger.info("多模态检索已启用，将在首次使用时尝试加载模型")
        else:
            if not Config.ENABLE_MULTIMODAL:
                logger.info("多模态检索未启用（配置关闭）")
            elif not self._init_success:
                logger.warning("多模态检索未启用（数据库未就绪）")

        # 优先从数据库还原 chunks
        if self._init_success and self._restore_chunks_from_db():
            self._rebuild_bm25()
            self._sync_multimodal_index()
            self.is_loaded = True
            logger.info(f"✅ 从数据库还原索引成功，共 {len(self.chunks)} 个文本块，BM25 已重建")
        else:
            self._load_chunks_data()
            if self.chunks:
                self._rebuild_bm25()
                self._sync_multimodal_index()
                self.is_loaded = True
                logger.info(f"✅ 从本地文件加载索引成功，共 {len(self.chunks)} 个文本块")
            else:
                self.is_loaded = False
                logger.warning("⚠️ 无法恢复索引，请重新索引文档")

    # ---------- 懒加载属性 + 健壮性 ----------
    @property
    def clip_retriever(self):
        """懒加载 CLIP 检索器，首次访问时实例化，并更新可用标志。失败后不再重试。"""
        if self._clip_retriever is None and Config.ENABLE_MULTIMODAL and self._init_success:
            # 检查是否已确认不可用（避免重复尝试导致大量 traceback）
            if getattr(self, "_clip_failed", False):
                return None
            try:
                self._clip_retriever = ClipRetriever()
                self._multimodal_available = True
                logger.info("多模态检索器懒加载成功")
            except Exception as e:
                logger.warning(f"多模态检索器不可用（CLIP模型未安装或损坏）: {e}")
                self._clip_retriever = None
                self._multimodal_available = False
                self._clip_failed = True
        return self._clip_retriever

    # ---------- 多模态索引同步 ----------
    def _is_image_metadata(self, meta: dict) -> bool:
        """判断 metadata 是否代表图片（兼容新旧格式）"""
        return (
            meta.get("type") == "image"
            or meta.get("category") == "Image"
            or (meta.get("image_path") is not None and not meta.get("missing", False))
        )

    def _resolve_image_path(self, image_path: str) -> str:
        """将 metadata 中的 image_path 解析为绝对路径（如果已经是绝对路径则直接返回）"""
        if not image_path:
            return ""
        if os.path.isabs(image_path):
            return image_path
        # 相对路径：尝试基于 DATA_DIR 拼接
        return os.path.join(Config.DATA_DIR, image_path)

    def _sync_multimodal_index(self):
        """将当前所有图片类型的 chunk 同步到多模态检索器（仅在可用时执行）"""
        if not (Config.ENABLE_MULTIMODAL and self._init_success and self._multimodal_available):
            return
        if self._clip_retriever is None:
            return
        try:
            image_docs = []
            for meta in self.chunk_metadata:
                if self._is_image_metadata(meta) and not meta.get("missing", False):
                    # 确保 image_path 是绝对路径，避免 CLIP 加载失败
                    img_path = meta.get("image_path")
                    if img_path:
                        abs_path = self._resolve_image_path(img_path)
                        if os.path.exists(abs_path):
                            # 复制一份 metadata，修正路径
                            new_meta = meta.copy()
                            new_meta["image_path"] = abs_path
                            doc = Document(page_content="", metadata=new_meta)
                            image_docs.append(doc)
                        else:
                            logger.warning(f"图片不存在，跳过同步: {abs_path}")
                    else:
                        # 如果没有 image_path，可能只有 image_url
                        logger.debug(f"图片文档缺少 image_path: {meta}")
            if image_docs:
                self._clip_retriever.rebuild_index_from_documents(image_docs)
                logger.info(f"多模态索引同步完成，共 {len(image_docs)} 张图片")
            else:
                self._clip_retriever.image_embeddings = []
                self._clip_retriever.image_metadatas = []
                self._clip_retriever.save_index()
                logger.info("多模态索引已清空")
        except Exception as e:
            logger.error(f"多模态索引同步失败: {e}", exc_info=True)
            self._multimodal_available = False

    def multimodal_search(self, query: str, top_k: int = Config.MULTIMODAL_TOP_K):
        """
        根据文本查询多模态图片检索结果，返回 (Document列表, 分数列表)。
        每个 Document 的 page_content 包含图片 Markdown 链接和描述，便于 LLM 直接输出图片。
        """
        if not (Config.ENABLE_MULTIMODAL and self._init_success and self._multimodal_available):
            if Config.ENABLE_MULTIMODAL and self._init_success and not self._multimodal_available:
                logger.debug("多模态检索跳过：模型未加载或加载失败")
            return [], []
        if self._clip_retriever is None:
            return [], []
        try:
            results = self._clip_retriever.search_by_text(query, top_k=top_k)
        except Exception as e:
            logger.error(f"多模态检索执行失败: {e}", exc_info=True)
            self._multimodal_available = False
            return [], []

        docs = []
        scores = []
        for meta, score in results:
            # 提取图片信息
            img_path = meta.get("image_path", "")
            caption = meta.get("image_caption", meta.get("caption", ""))
            # 构建 Markdown 图片语法
            if img_path:
                # 优先使用 image_url 字段，如果没有则根据 image_path 生成
                image_url = meta.get("image_url")
                if not image_url:
                    # 将绝对路径转换为 /images/ 形式
                    if os.path.isabs(img_path) and Config.IMAGES_DIR in img_path:
                        rel = os.path.relpath(img_path, Config.IMAGES_DIR)
                        image_url = f"/images/{rel}"
                    else:
                        image_url = img_path  # fallback
                img_markdown = f"![{caption or '图片'}]({image_url})"
            else:
                img_markdown = ""

            text_parts = []
            if caption:
                text_parts.append(f"相关图片描述：{caption}")
            if img_markdown:
                text_parts.append(img_markdown)
            if not text_parts:
                text_parts.append(f"[相关图片] {img_path}")
            page_content = "\n".join(text_parts)

            doc = Document(
                page_content=page_content,
                metadata={**meta, "source_type": "multimodal", "image_markdown": img_markdown},
            )
            docs.append(doc)
            scores.append(score)

        record_vision_call()
        record_retrieval(mode="multimodal", doc_count=len(docs))
        return docs, scores

    # ---------- 辅助方法 ----------
    def _sync_embed(self, texts: list[str]) -> np.ndarray:
        if not self._init_success:
            return np.zeros((len(texts), self.dim))
        # Redis 嵌入缓存
        cached = np.zeros((len(texts), self.dim))
        uncached_indices = []
        uncached_texts = []
        try:
            import redis as rds

            rc = rds.Redis(host="localhost", port=6379, db=2, decode_responses=False)
            for i, t in enumerate(texts):
                key = f"emb:{hashlib.md5(t.encode()).hexdigest()}"
                val = rc.get(key)
                if val:
                    cached[i] = np.frombuffer(val, dtype=np.float32)
                else:
                    uncached_indices.append(i)
                    uncached_texts.append(t)
        except Exception:
            uncached_indices = list(range(len(texts)))
            uncached_texts = texts

        if uncached_texts:
            try:
                response = ollama.embed(model=Config.EMBEDDING_MODEL, input=uncached_texts)
                embeddings = np.array(response["embeddings"], dtype=np.float32)
                for i, emb in zip(uncached_indices, embeddings, strict=False):
                    cached[i] = emb
                # 写入 Redis 缓存
                try:
                    import redis as _rds

                    _rc = _rds.Redis(host="localhost", port=6379, db=2, decode_responses=False)
                    pipe = _rc.pipeline()
                    for t, emb in zip(uncached_texts, embeddings, strict=False):
                        key = f"emb:{hashlib.md5(t.encode()).hexdigest()}"
                        pipe.set(key, emb.tobytes(), ex=86400)
                    pipe.execute()
                except Exception:
                    pass
                return cached
            except Exception as e:
                logger.error(f"Ollama 嵌入失败: {e}")
                return np.zeros((len(texts), self.dim))
        return cached

    def _get_file_hash(self, file_path: str) -> str:
        with open(file_path, "rb") as f:
            return hashlib.md5(f.read()).hexdigest()

    def _load_doc_meta(self):
        meta_path = os.path.join(Config.INDEX_DIR, "doc_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, encoding="utf-8") as f:
                self.doc_meta = json.load(f)
        else:
            self.doc_meta = {}

    def _save_doc_meta(self):
        os.makedirs(Config.INDEX_DIR, exist_ok=True)
        meta_path = os.path.join(Config.INDEX_DIR, "doc_meta.json")
        with open(meta_path, "w", encoding="utf-8") as f:
            json.dump(self.doc_meta, f, indent=2, ensure_ascii=False)

    def _save_chunks_data(self):
        os.makedirs(Config.INDEX_DIR, exist_ok=True)
        with open(self.chunks_data_path, "wb") as f:
            pickle.dump((self.chunks, self.chunk_images, self.chunk_metadata), f)
        logger.info(f"Chunks 数据已保存到 {self.chunks_data_path}")

    def _load_chunks_data(self):
        # Check shared cache first
        if _shared["chunks"] is not None:
            self.chunks = _shared["chunks"]
            self.chunk_metadata = _shared["chunk_metadata"]
            self.chunk_images = _shared["chunk_images"]
            self.bm25 = _shared["bm25"]
            self.doc_meta = _shared["doc_meta"]
            self.graph_builder = _shared["graph_builder"]
            logger.info(f"从共享缓存加载 {len(self.chunks)} 个文本块（跳过重复加载）")
            return

        if os.path.exists(self.chunks_data_path):
            try:
                with open(self.chunks_data_path, "rb") as f:
                    data = pickle.load(f)
                    if len(data) == 3:
                        self.chunks, self.chunk_images, self.chunk_metadata = data
                    else:
                        self.chunks, self.chunk_images = data
                        self.chunk_metadata = [{} for _ in self.chunks]
                    logger.info(f"从文件加载 {len(self.chunks)} 个文本块")
            except Exception as e:
                logger.error(f"加载 chunks 数据失败: {e}", exc_info=True)
        else:
            logger.info("chunks_data.pkl 不存在")

        # Populate shared cache
        _shared["chunks"] = self.chunks
        _shared["chunk_metadata"] = self.chunk_metadata
        _shared["chunk_images"] = self.chunk_images

    def _restore_chunks_from_db(self) -> bool:
        if not self._init_success:
            return False
        try:
            with self.db_engine.connect() as conn:
                result = conn.execute(
                    text(f"SELECT content, langchain_metadata FROM {self.table_name} ORDER BY langchain_id")
                )
                rows = result.fetchall()
            if not rows:
                logger.info("向量表中没有数据，无法还原 chunks")
                return False
            chunks = []
            chunk_images = []
            chunk_metadata = []
            for row in rows:
                content = row[0]
                metadata = row[1] if row[1] else {}
                chunks.append(content)
                images = metadata.get("images", []) if isinstance(metadata, dict) else []
                chunk_images.append(images)
                chunk_metadata.append(metadata)
            self.chunks = chunks
            self.chunk_images = chunk_images
            self.chunk_metadata = chunk_metadata
            logger.info(f"从数据库还原 {len(self.chunks)} 个文本块，图片信息 {len(self.chunk_images)} 条")
            return True
        except Exception as e:
            logger.error(f"从数据库还原 chunks 失败: {e}", exc_info=True)
            return False

    def _rebuild_bm25(self):
        if _shared["bm25"] is not None and _shared["chunks"] is self.chunks:
            self.bm25 = _shared["bm25"]
            return
        if not self.chunks:
            logger.warning("chunks 为空，跳过 BM25 构建")
            return
        tokenized = [list(jieba.cut(c)) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)
        _shared["bm25"] = self.bm25
        logger.info(f"BM25 索引构建完成，文档数: {len(self.chunks)}")

    def _bm25_scores(self, query: str) -> list:
        if not self.bm25 or not self.chunks:
            return []
        tokenized_q = list(jieba.cut(query))
        # TF-IDF 关键词加权：提取重要关键词重复追加，提升 BM25 召回精度
        try:
            keywords = jieba.analyse.extract_tags(query, topK=5, withWeight=False)
            tokenized_q.extend(keywords)
        except Exception:
            pass
        scores = self.bm25.get_scores(tokenized_q)
        return scores.tolist() if hasattr(scores, "tolist") else scores

    def _retrieve_from_graph(self, query: str, top_k: int = 3) -> list:
        if not self._init_success or self.graph_builder is None:
            return []
        try:
            indices = self.graph_builder.retrieve_by_entities_with_hops(query, hops=Config.GRAPH_HOPS, top_k=top_k)
            return [i for i in indices if i < len(self.chunks)]
        except Exception as e:
            logger.error(f"图谱检索失败: {e}")
            return []

    def load_documents(self, file_paths, progress_callback=None, incremental=True):
        if not self._init_success:
            raise RuntimeError("检索器未正确初始化，请检查数据库配置和 pgvector 扩展。")

        if not incremental:
            logger.info("全量重建索引：清空现有向量表...")
            try:
                with self.db_engine.connect() as conn:
                    conn.execute(f"DROP TABLE IF EXISTS {self.table_name}")
                    conn.commit()
            except Exception as e:
                logger.warning(f"删除旧表失败: {e}")

            self.pg_engine.init_vectorstore_table(
                table_name=self.table_name, vector_size=self.dim, overwrite_existing=True
            )

            embedding = OllamaEmbeddings(Config.EMBEDDING_MODEL, self.dim)
            self.vector_store = PGVectorStore.create_sync(
                engine=self.pg_engine,
                table_name=self.table_name,
                embedding_service=embedding,
            )

            try:
                with self.db_engine.connect() as conn:
                    conn.execute(
                        f"CREATE INDEX IF NOT EXISTS hnsw_idx ON {self.table_name}"
                        f" USING hnsw (embedding vector_cosine_ops)"
                        f" WITH (m = {Config.VECTOR_HNSW_M}, ef_construction = {Config.VECTOR_HNSW_EF_CONSTRUCTION});"
                    )
                    conn.commit()
            except Exception as e:
                logger.debug(f"Index creation: {e}")

            self.chunks = []
            self.chunk_metadata = []
            self.chunk_images = []
            self.bm25 = None
            self.doc_meta = {}
            self.graph_builder = None

        all_docs = []
        new_file_hashes = []
        for path in file_paths:
            file_hash = self._get_file_hash(path)
            if incremental and file_hash in self.doc_meta:
                logger.info(f"文件 {path} 已存在，跳过")
                continue
            try:
                docs = load_single_document(path)
                all_docs.extend(docs)
                new_file_hashes.append(file_hash)
                self.doc_meta[file_hash] = {"path": path}
            except Exception as e:
                logger.error(f"加载文件 {path} 失败: {e}")

        if not all_docs:
            return len(self.chunks)

        # 智能分块
        chunks = smart_split_markdown(all_docs, chunk_size=Config.CHUNK_SIZE, chunk_overlap=Config.CHUNK_OVERLAP)

        new_texts = [c.page_content for c in chunks]
        new_metadata = [c.metadata for c in chunks]
        new_images = [c.metadata.get("images", []) for c in chunks]

        start_index = len(self.chunks)
        self.chunks.extend(new_texts)
        self.chunk_metadata.extend(new_metadata)
        self.chunk_images.extend(new_images)
        self._rebuild_bm25()

        # 准备向量存储（上下文增强分块）
        docs_to_store = []
        for idx, text in enumerate(new_texts):
            import re

            has_formula = bool(re.search(r"[\+\-\*/=]|[0-9]+\s*[\+\-\*/]|[αβγδεζηθικλμνξοπρστυφχψω∑∏∫√∂Δμσδ]", text))
            meta = new_metadata[idx].copy()
            meta["chunk_index"] = start_index + idx
            meta["is_formula"] = has_formula

            # 上下文增强：嵌入时拼接文档名和章节路径
            source = meta.get("source", "")
            section = meta.get("section", "")
            filename = os.path.basename(source) if source else ""
            context_parts = []
            if filename:
                context_parts.append(filename)
            if section and section != "Root":
                context_parts.append(section)
            context_prefix = f"[{' > '.join(context_parts)}]\n" if context_parts else ""

            meta["context_prefix"] = context_prefix.strip()
            embed_text = context_prefix + text if context_prefix else text
            doc = Document(page_content=embed_text, metadata=meta)
            docs_to_store.append(doc)

        # 过滤 NUL 字节
        filtered_docs = []
        for doc in docs_to_store:
            if "\x00" in doc.page_content:
                logger.warning(f"跳过包含 NUL 字节的文档，来源: {doc.metadata.get('source', '未知')}")
                continue
            filtered_docs.append(doc)
        docs_to_store = filtered_docs
        if not docs_to_store:
            logger.warning("没有有效的文档可写入数据库，索引终止")
            return len(self.chunks)

        batch_size = 100
        for i in range(0, len(docs_to_store), batch_size):
            batch = docs_to_store[i : i + batch_size]
            try:
                self.vector_store.add_documents(batch)
                logger.info(f"成功写入批次 {i // batch_size + 1}，{len(batch)} 条")
            except Exception as e:
                logger.error(f"批量写入失败: {e}")
                raise
            if progress_callback:
                progress = min((i + batch_size) / len(docs_to_store), 1.0)
                progress_callback(progress)

        # 知识图谱更新
        if Config.ENABLE_GRAPH:
            try:
                if self.graph_builder is None:
                    from core.graph_builder import GraphBuilder

                    self.graph_builder = GraphBuilder()
                    self.graph_builder.build_from_chunks(self.chunks)
                    logger.info("知识图谱全量构建完成")
                else:
                    old_count = len(self.chunks) - len(new_texts)
                    self.graph_builder.update_from_chunks(new_texts, old_count)
                    logger.info("知识图谱增量更新完成")
            except Exception as e:
                logger.error(f"知识图谱更新失败: {e}")

        # 多模态索引同步（增量添加图片） - 修复路径处理
        if (
            Config.ENABLE_MULTIMODAL
            and self._init_success
            and self._multimodal_available
            and self._clip_retriever is not None
        ):
            new_image_docs = []
            for c in chunks:
                meta = c.metadata
                if self._is_image_metadata(meta) and not meta.get("missing", False):
                    # 确保 image_path 可被解析
                    img_path = meta.get("image_path")
                    if img_path:
                        abs_path = self._resolve_image_path(img_path)
                        if os.path.exists(abs_path):
                            # 更新 metadata 中的 image_path 为绝对路径，方便后续使用
                            meta["image_path"] = abs_path
                            new_image_docs.append(c)
                        else:
                            logger.warning(f"图片不存在，跳过增量索引: {abs_path}")
                    else:
                        # 如果没有 image_path，但可能有 image_url（例如网络图片）
                        logger.debug(f"图片文档缺少 image_path，无法加入多模态索引: {meta.get('source', 'unknown')}")
            if new_image_docs:
                try:
                    for img_doc in new_image_docs:
                        img_path = img_doc.metadata.get("image_path")
                        if img_path and os.path.exists(img_path):
                            self._clip_retriever.add_image(img_path, img_doc.metadata)
                    self._clip_retriever.save_index()
                    logger.info(f"多模态索引新增 {len(new_image_docs)} 张图片")
                except Exception as e:
                    logger.error(f"多模态索引增量更新失败: {e}", exc_info=True)
                    self._multimodal_available = False
            else:
                # 没有新增图片，但仍需确保索引与当前数据一致
                self._sync_multimodal_index()

        self.is_loaded = True
        self._save_doc_meta()
        self._save_chunks_data()
        return len(self.chunks)

    # ---------- 多查询检索（Multi-Query Retrieval） ----------
    def _multi_query_retrieve(self, query: str, top_k: int) -> tuple:
        """
        使用多个查询变体并行检索，然后去重融合。
        需要 QueryOptimizer 中有 generate_multi_queries 方法。
        如果未配置或失败，则退化到基础检索（_ensemble_search）。
        """
        # 检查是否启用多查询
        if not getattr(Config, "ENABLE_MULTI_QUERY", False):
            # 回退到基础检索（不再调用 hybrid_search，避免递归）
            texts, indices, _ = self._ensemble_search(query, top_k)
            return texts, indices

        # 生成多查询
        try:
            from core.query_optimizer import QueryOptimizer

            qo = QueryOptimizer()
            queries = qo.generate_multi_queries(query, num_queries=3)
            if not queries or len(queries) == 1:
                # 退化到基础检索
                texts, indices, _ = self._ensemble_search(query, top_k)
                return texts, indices
        except Exception as e:
            logger.warning(f"生成多查询失败: {e}，回退到基础检索")
            texts, indices, _ = self._ensemble_search(query, top_k)
            return texts, indices

        # 并行检索：每个查询使用基础检索 _ensemble_search
        all_texts = []
        all_indices = []
        seen_texts = set()
        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            futures = [executor.submit(self._ensemble_search, q, top_k) for q in queries]
            for future in futures:
                try:
                    texts, indices, _ = future.result()
                    for t, idx in zip(texts, indices, strict=False):
                        if t not in seen_texts:
                            seen_texts.add(t)
                            all_texts.append(t)
                            all_indices.append(idx)
                except Exception as e:
                    logger.error(f"多查询检索子任务失败: {e}")
        return all_texts, all_indices

    def hybrid_search(self, query, top_k=Config.TOP_K, alpha=Config.ALPHA):
        start_time = time.perf_counter()
        if not self._init_success:
            logger.warning("检索器未初始化成功，无法检索")
            return [], []

        # 动态计算 alpha（如果启用）
        if getattr(Config, "DYNAMIC_ALPHA", False):
            alpha = self._get_dynamic_alpha(query)
            logger.debug(f"动态 alpha 计算: {alpha}")
        else:
            alpha = Config.ALPHA

        # 数据同步（首次同步后跳过）
        if not self.is_loaded:
            if self._restore_chunks_from_db():
                self._rebuild_bm25()
                self.is_loaded = True
                logger.debug(f"从数据库同步成功，当前 chunks: {len(self.chunks)}")
            elif self.chunks:
                self._rebuild_bm25()
                self.is_loaded = True
                logger.debug(f"使用本地 chunks，数量: {len(self.chunks)}")
            else:
                logger.warning("无法加载任何索引数据，检索结果为空")
                return [], []

        if self.bm25 is None and self.chunks:
            self._rebuild_bm25()

        # 多查询检索优先
        if getattr(Config, "ENABLE_MULTI_QUERY", False):
            final_texts, final_indices = self._multi_query_retrieve(query, top_k)
            final_metadatas = [self.chunk_metadata[i] for i in final_indices]
        else:
            final_texts, final_indices, final_metadatas = self._ensemble_search(query, top_k)

        if not final_texts:
            logger.warning("多路融合无结果，降级为纯 BM25")
            bm25_scores = self._bm25_scores(query)
            if bm25_scores:
                scored = sorted(
                    [(self.chunks[i], bm25_scores[i], i) for i in range(len(self.chunks)) if bm25_scores[i] > 0],
                    key=lambda x: x[1],
                    reverse=True,
                )[:top_k]
                final_texts = [x[0] for x in scored]
                final_indices = [x[2] for x in scored]
                final_metadatas = [self.chunk_metadata[i] for i in final_indices]

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"多路融合检索完成，耗时 {elapsed:.2f} ms，返回 {len(final_texts)} 个结果")
        record_retrieval(mode="final", doc_count=len(final_texts))
        return final_texts, final_indices

    def get_chunk_images(self, indices):
        if not self._init_success or not indices:
            return []
        valid = [i for i in indices if 0 <= i < len(self.chunk_images)]
        return [self.chunk_images[i] for i in valid]

    def delete_document_by_hash(self, file_hash: str) -> bool:
        if not self._init_success:
            return False
        if file_hash not in self.doc_meta:
            return False
        file_path = self.doc_meta[file_hash].get("path")
        del self.doc_meta[file_hash]
        self._save_doc_meta()
        if not self.doc_meta and os.path.exists(self.chunks_data_path):
            os.remove(self.chunks_data_path)
            logger.info("所有文档已删除，已清理 chunks 数据")
        if (
            Config.ENABLE_MULTIMODAL
            and self._init_success
            and self._multimodal_available
            and self._clip_retriever is not None
            and file_path
        ):
            try:
                to_remove = []
                for meta in self.chunk_metadata:
                    if meta.get("source") == file_path and self._is_image_metadata(meta):
                        img_path = meta.get("image_path")
                        if img_path:
                            to_remove.append(img_path)
                for img_path in to_remove:
                    self._clip_retriever.remove_image(img_path)
                self._clip_retriever.save_index()
                logger.info(f"从多模态索引删除 {len(to_remove)} 张图片")
            except Exception as e:
                logger.error(f"删除文档时多模态索引更新失败: {e}", exc_info=True)
                self._multimodal_available = False
        return True

    def expand_context(self, indices: list[int], before: int = 1, after: int = 1) -> list[int]:
        if not self.chunks or not indices:
            return []
        expanded = set()
        for idx in indices:
            expanded.add(idx)
            for offset in range(1, before + 1):
                if idx - offset >= 0:
                    expanded.add(idx - offset)
            for offset in range(1, after + 1):
                if idx + offset < len(self.chunks):
                    expanded.add(idx + offset)
        return sorted(expanded)

    def extract_keywords(self, text: str, top_k: int = 5) -> str:
        keywords = jieba.analyse.extract_tags(text, topK=top_k)
        return " ".join(keywords)

    def _ensemble_search(self, query: str, top_k: int = Config.TOP_K):
        """
        多路召回融合：向量 + BM25 + 图谱 + 多模态
        返回 (texts, indices, metadatas)
        """
        with ThreadPoolExecutor(max_workers=4) as executor:
            future_vector = executor.submit(self.vector_store.similarity_search_with_score, query, k=top_k * 2)
            future_bm25 = executor.submit(self._bm25_scores, query)
            future_graph = executor.submit(self._retrieve_from_graph, query, top_k)
            # 只有多模态可用时才提交任务
            if Config.ENABLE_MULTIMODAL and self._init_success and self._multimodal_available:
                future_multimodal = executor.submit(self.multimodal_search, query, Config.MULTIMODAL_TOP_K)
            else:
                future_multimodal = None

            try:
                vector_res = future_vector.result()
            except Exception as e:
                logger.error(f"向量检索失败: {e}")
                vector_res = []
            bm25_scores = future_bm25.result() or []
            graph_indices = future_graph.result()
            multimodal_docs = []
            multimodal_scores = []
            if future_multimodal:
                try:
                    multimodal_docs, multimodal_scores = future_multimodal.result()
                except Exception as e:
                    logger.error(f"多模态检索失败: {e}")

        candidates = {}

        # 向量检索
        for rank, (doc, _distance) in enumerate(vector_res[: top_k * 2], start=1):
            idx = doc.metadata.get("chunk_index", -1)
            if idx != -1 and 0 <= idx < len(self.chunks):
                if idx not in candidates:
                    candidates[idx] = {"text": self.chunks[idx], "ranks": [], "metadata": self.chunk_metadata[idx]}
                candidates[idx]["ranks"].append(("vector", rank))

        # BM25
        if bm25_scores:
            scored_idx = sorted(
                [(i, bm25_scores[i]) for i in range(len(bm25_scores)) if bm25_scores[i] > 0],
                key=lambda x: x[1],
                reverse=True,
            )
            for rank, (idx, _) in enumerate(scored_idx[: top_k * 2], start=1):
                if idx not in candidates:
                    candidates[idx] = {"text": self.chunks[idx], "ranks": [], "metadata": self.chunk_metadata[idx]}
                candidates[idx]["ranks"].append(("bm25", rank))

        # 图谱
        for rank, idx in enumerate(graph_indices[:top_k], start=1):
            if idx not in candidates:
                candidates[idx] = {"text": self.chunks[idx], "ranks": [], "metadata": self.chunk_metadata[idx]}
            candidates[idx]["ranks"].append(("graph", rank))

        # 多模态（虚拟索引）
        multimodal_virtual_start = len(self.chunks)
        for rank, (doc, score) in enumerate(zip(multimodal_docs, multimodal_scores, strict=False), start=1):
            idx = multimodal_virtual_start + rank - 1
            candidates[idx] = {"text": doc.page_content, "ranks": [("multimodal", rank)], "metadata": doc.metadata}

        # RRF 融合
        K = 60
        rrf_scores = {}
        for idx, data in candidates.items():
            score = 0.0
            for _, rank in data["ranks"]:
                score += 1.0 / (K + rank)
            rrf_scores[idx] = score

        sorted_items = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        final_texts = []
        final_indices = []
        final_metadatas = []
        for idx, _ in sorted_items:
            data = candidates[idx]
            final_texts.append(data["text"])
            final_indices.append(idx)
            final_metadatas.append(data["metadata"])
        return final_texts, final_indices, final_metadatas

    def _get_dynamic_alpha(self, query: str) -> float:
        """动态决定 BM25 权重"""
        words = query.split()
        if len(words) <= 4:
            return 0.7
        if len(words) >= 15:
            return 0.3
        if any(re.search(r"[A-Z]{2,}", w) or re.search(r"\d", w) for w in words):
            return 0.6
        return Config.ALPHA
