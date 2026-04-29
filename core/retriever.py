import asyncio
import sys

if sys.platform == 'win32':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
from sqlalchemy import text
import os
import jieba
import json
import hashlib
import pickle
import numpy as np
import ollama
from rank_bm25 import BM25Okapi
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
from langchain_postgres import PGVectorStore, PGEngine
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from config import Config
from utils.维护.document_loader import load_single_document
from sqlalchemy import create_engine
from concurrent.futures import ThreadPoolExecutor
import time
import logging
import jieba.analyse
from core.intent_classifier import IntentClassifier  # 新增导入

logger = logging.getLogger(__name__)


class OllamaEmbeddings(Embeddings):
    def __init__(self, model: str, dim: int):
        self.model = model
        self.dim = dim

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        try:
            response = ollama.embed(model=self.model, input=texts)
            return response['embeddings']
        except Exception as e:
            logger.error(f"Ollama 嵌入失败: {e}")
            return [[0.0] * self.dim for _ in texts]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]

    async def aembed_documents(self, texts: list[str]) -> list[list[float]]:
        return self.embed_documents(texts)

    async def aembed_query(self, text: str) -> list[float]:
        return (await self.aembed_documents([text]))[0]


class HybridRetriever:
    def __init__(self):
        self.dim = Config.EMBEDDING_DIM
        self.chunks = []
        self.chunk_metadata = []
        self.chunk_images = []
        self.bm25 = None
        self.is_loaded = False
        self.doc_meta = {}
        self.graph_builder = None
        self.chunks_data_path = os.path.join(Config.INDEX_DIR, "chunks_data.pkl")

        # 初始化意图分类器
        self.intent_classifier = IntentClassifier()

        # 1. 加载文档元数据
        self._load_doc_meta()

        # 2. 数据库初始化
        self._init_success = False
        try:
            sync_db_url = Config.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
            self.db_engine = create_engine(
                sync_db_url,
                pool_size=10,
                max_overflow=20,
                pool_pre_ping=True,
                echo=False
            )
            self.pg_engine = PGEngine.from_connection_string(url=sync_db_url)
            self.table_name = "brianrag_vectors"
            self.pg_engine.init_vectorstore_table(
                table_name=self.table_name,
                vector_size=self.dim,
                overwrite_existing=True
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
                        f"CREATE INDEX IF NOT EXISTS hnsw_idx ON {self.table_name} USING hnsw (embedding vector_cosine_ops) WITH (m = 32, ef_construction = 200);"
                    )
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

        # 3. 优先从数据库还原 chunks（关键改动）
        if self._init_success and self._restore_chunks_from_db():
            self._rebuild_bm25()
            self.is_loaded = True
            logger.info(f"✅ 从数据库还原索引成功，共 {len(self.chunks)} 个文本块，BM25 已重建")
        else:
            # 4. 降级：从本地文件加载 chunks（兜底）
            self._load_chunks_data()
            if self.chunks:
                self._rebuild_bm25()
                self.is_loaded = True
                logger.info(f"✅ 从本地文件加载索引成功，共 {len(self.chunks)} 个文本块")
            else:
                self.is_loaded = False
                logger.warning("⚠️ 无法恢复索引，请重新索引文档")

    # ---------- 辅助方法 ----------
    def _sync_embed(self, texts: list[str]) -> np.ndarray:
        if not self._init_success:
            return np.zeros((len(texts), self.dim))
        try:
            response = ollama.embed(model=Config.EMBEDDING_MODEL, input=texts)
            return np.array(response['embeddings'])
        except Exception as e:
            logger.error(f"Ollama 嵌入失败: {e}")
            return np.zeros((len(texts), self.dim))

    def _get_file_hash(self, file_path: str) -> str:
        with open(file_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()

    def _load_doc_meta(self):
        meta_path = os.path.join(Config.INDEX_DIR, "doc_meta.json")
        if os.path.exists(meta_path):
            with open(meta_path, 'r', encoding='utf-8') as f:
                self.doc_meta = json.load(f)
        else:
            self.doc_meta = {}

    def _save_doc_meta(self):
        os.makedirs(Config.INDEX_DIR, exist_ok=True)
        meta_path = os.path.join(Config.INDEX_DIR, "doc_meta.json")
        with open(meta_path, 'w', encoding='utf-8') as f:
            json.dump(self.doc_meta, f, indent=2, ensure_ascii=False)

    def _save_chunks_data(self):
        os.makedirs(Config.INDEX_DIR, exist_ok=True)
        with open(self.chunks_data_path, "wb") as f:
            pickle.dump((self.chunks, self.chunk_images, self.chunk_metadata), f)
        logger.info(f"Chunks 数据已保存到 {self.chunks_data_path}")

    def _load_chunks_data(self):
        if os.path.exists(self.chunks_data_path):
            try:
                with open(self.chunks_data_path, "rb") as f:
                    data = pickle.load(f)
                    if len(data) == 3:
                        self.chunks, self.chunk_images, self.chunk_metadata = data
                    else:
                        # 兼容旧版本（只有 chunks 和 images）
                        self.chunks, self.chunk_images = data
                        self.chunk_metadata = [{} for _ in self.chunks]
                    logger.info(f"从文件加载 {len(self.chunks)} 个文本块")
            except Exception as e:
                logger.error(f"加载 chunks 数据失败: {e}", exc_info=True)
        else:
            logger.info("chunks_data.pkl 不存在")

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
        if not self.chunks:
            logger.warning("chunks 为空，跳过 BM25 构建")
            return
        tokenized = [list(jieba.cut(c)) for c in self.chunks]
        self.bm25 = BM25Okapi(tokenized)
        logger.info(f"BM25 索引构建完成，文档数: {len(self.chunks)}")

    def _bm25_scores(self, query: str) -> list:
        if not self.bm25 or not self.chunks:
            return []
        tokenized_q = list(jieba.cut(query))
        scores = self.bm25.get_scores(tokenized_q)
        return scores.tolist() if hasattr(scores, 'tolist') else scores

    def _retrieve_from_graph(self, query: str, top_k: int = 3) -> list:
        if not self._init_success or self.graph_builder is None:
            return []
        try:
            indices = self.graph_builder.retrieve_by_entities_with_hops(
                query, hops=Config.GRAPH_HOPS, top_k=top_k
            )
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
                table_name=self.table_name,
                vector_size=self.dim,
                overwrite_existing=True
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
                        f"CREATE INDEX IF NOT EXISTS hnsw_idx ON {self.table_name} USING hnsw (embedding vector_cosine_ops) WITH (m = 32, ef_construction = 200);"
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

        # 智能分块（如果 smart_splitter 存在）
        try:
            from core.smart_splitter import smart_split_markdown
            chunks = smart_split_markdown(all_docs, chunk_size=Config.CHUNK_SIZE, chunk_overlap=Config.CHUNK_OVERLAP)
        except ImportError:
            splitter = RecursiveCharacterTextSplitter(
                chunk_size=Config.CHUNK_SIZE,
                chunk_overlap=Config.CHUNK_OVERLAP
            )
            chunks = splitter.split_documents(all_docs)

        new_texts = [c.page_content for c in chunks]
        new_metadata = [c.metadata for c in chunks]
        new_images = [c.metadata.get("images", []) for c in chunks]

        start_index = len(self.chunks)
        self.chunks.extend(new_texts)
        self.chunk_metadata.extend(new_metadata)
        self.chunk_images.extend(new_images)
        self._rebuild_bm25()

        # 准备向量存储，并确保每个 Document 的 metadata 中包含 chunk_index 和 is_formula
        docs_to_store = []
        for idx, text in enumerate(new_texts):
            # 判断是否包含公式（简单启发式）
            import re
            has_formula = bool(re.search(r'[\+\-\*/=]|[0-9]+\s*[\+\-\*/]|[αβγδεζηθικλμνξοπρστυφχψω∑∏∫√∂Δμσδ]', text))
            meta = new_metadata[idx].copy()
            meta["chunk_index"] = start_index + idx
            meta["is_formula"] = has_formula
            doc = Document(page_content=text, metadata=meta)
            docs_to_store.append(doc)

        batch_size = 100
        for i in range(0, len(docs_to_store), batch_size):
            batch = docs_to_store[i:i + batch_size]
            try:
                self.vector_store.add_documents(batch)
                logger.info(f"成功写入批次 {i // batch_size + 1}，{len(batch)} 条")
            except Exception as e:
                logger.error(f"批量写入失败: {e}")
                raise  # 索引失败，终止
            if progress_callback:
                progress = min((i + batch_size) / len(docs_to_store), 1.0)
                progress_callback(progress)

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

        self.is_loaded = True
        self._save_doc_meta()
        self._save_chunks_data()
        return len(self.chunks)

    def hybrid_search(self, query, top_k=Config.TOP_K, alpha=Config.ALPHA):
        start_time = time.perf_counter()
        if not self._init_success:
            logger.warning("检索器未初始化成功，无法检索")
            return [], []

        # 数据同步（略，保持不变）
        if self._restore_chunks_from_db():
            self._rebuild_bm25()
            logger.info(f"从数据库同步成功，当前 chunks 数量: {len(self.chunks)}")
        else:
            self._load_chunks_data()
            if self.chunks:
                self._rebuild_bm25()
                logger.info(f"从本地文件加载 chunks，数量: {len(self.chunks)}")
            else:
                logger.warning("无法加载任何索引数据，检索结果为空")
                return [], []

        if self.bm25 is None and self.chunks:
            self._rebuild_bm25()

        # --- 多路融合检索 ---
        final_texts, final_indices = self._ensemble_search(query, top_k)

        # 如果融合结果为空，降级为纯 BM25（兜底）
        if not final_texts:
            logger.warning("多路融合无结果，降级为纯 BM25")
            bm25_scores = self._bm25_scores(query)
            if bm25_scores:
                scored = sorted(
                    [(self.chunks[i], bm25_scores[i], i) for i in range(len(self.chunks)) if bm25_scores[i] > 0],
                    key=lambda x: x[1], reverse=True)[:top_k]
                final_texts = [x[0] for x in scored]
                final_indices = [x[2] for x in scored]

        elapsed = (time.perf_counter() - start_time) * 1000
        logger.info(f"多路融合检索完成，耗时 {elapsed:.2f} ms，返回 {len(final_texts)} 个结果")
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
        del self.doc_meta[file_hash]
        self._save_doc_meta()
        if not self.doc_meta and os.path.exists(self.chunks_data_path):
            os.remove(self.chunks_data_path)
            logger.info("所有文档已删除，已清理 chunks 数据")
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

    def _ensemble_search(self, query: str, top_k: int = Config.TOP_K) -> tuple[list, list]:
        """
        多路召回融合：向量 + BM25 + 图谱
        使用 RRF (倒数排序融合) 合并结果
        """
        # 1. 并行执行各路检索
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_vector = executor.submit(
                self.vector_store.similarity_search_with_score, query, k=top_k * 2
            )
            future_bm25 = executor.submit(self._bm25_scores, query)
            future_graph = executor.submit(self._retrieve_from_graph, query, top_k)

            try:
                vector_res = future_vector.result()
            except Exception as e:
                logger.error(f"向量检索失败: {e}")
                vector_res = []
            bm25_scores = future_bm25.result() or []
            graph_indices = future_graph.result()

        # 2. 构建候选文档集合，记录每篇文档在各检索器中的排名
        candidates = {}  # key: chunk_index, value: {'text': str, 'ranks': []}

        # 向量检索结果 (按距离升序，距离越小越相关)
        for rank, (doc, distance) in enumerate(vector_res[:top_k * 2], start=1):
            idx = doc.metadata.get("chunk_index", -1)
            if idx != -1 and 0 <= idx < len(self.chunks):
                if idx not in candidates:
                    candidates[idx] = {'text': self.chunks[idx], 'ranks': []}
                candidates[idx]['ranks'].append(('vector', rank))

        # BM25 结果 (按分数降序)
        if bm25_scores:
            # 将 BM25 分数转换为排名（分数高的排名靠前）
            scored_idx = sorted([(i, bm25_scores[i]) for i in range(len(bm25_scores)) if bm25_scores[i] > 0],
                                key=lambda x: x[1], reverse=True)
            for rank, (idx, _) in enumerate(scored_idx[:top_k * 2], start=1):
                if idx not in candidates:
                    candidates[idx] = {'text': self.chunks[idx], 'ranks': []}
                candidates[idx]['ranks'].append(('bm25', rank))

        # 图谱检索结果 (按实体匹配度排序，已有顺序)
        for rank, idx in enumerate(graph_indices[:top_k], start=1):
            if idx not in candidates:
                candidates[idx] = {'text': self.chunks[idx], 'ranks': []}
            candidates[idx]['ranks'].append(('graph', rank))

        # 3. RRF 融合评分
        K = 60  # RRF 常数，通常为 60
        rrf_scores = {}
        for idx, data in candidates.items():
            score = 0.0
            for _, rank in data['ranks']:
                score += 1.0 / (K + rank)
            rrf_scores[idx] = score

        # 4. 按融合分数排序，取前 top_k
        sorted_idx = sorted(rrf_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        final_texts = [self.chunks[idx] for idx, _ in sorted_idx]
        final_indices = [idx for idx, _ in sorted_idx]
        return final_texts, final_indices