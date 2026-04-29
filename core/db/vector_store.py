# core/db/vector_store.py
import logging
from typing import List, Tuple

from langchain_postgres import PGEngine, PGVectorStore
from langchain_core.documents import Document
from sqlalchemy import create_engine

from config import Config
from core.retriever import HybridRetriever  # 仅用于 type hint

logger = logging.getLogger(__name__)

class PGVectorManager:
    def __init__(self, embedder):
        self.embedder = embedder
        self.engine = create_engine(Config.DATABASE_URL)
        self.pg_engine = PGEngine.from_engine(engine=self.engine)
        self.vector_store = None
        self._init_table()

    def _init_table(self):
        """确保向量表存在，并创建索引（如果未创建）"""
        self.vector_store = PGVectorStore.create_sync(
            engine=self.pg_engine,
            table_name=Config.VECTOR_TABLE_NAME,
            embedding_service=self.embedder._sync_embed,  # 复用嵌入函数
            # 注意：PGVectorStore 内部会调用 embedding_service 生成向量并存储
        )
        # 可选：创建 HNSW 索引以提高检索速度（首次调用需要）
        self._create_index_if_not_exists()

    def _create_index_if_not_exists(self):
        """为向量表创建 HNSW 索引（若不存在）"""
        with self.engine.connect() as conn:
            # 检查索引是否存在
            result = conn.execute(
                "SELECT 1 FROM pg_indexes WHERE indexname = 'brianrag_vectors_embedding_idx'"
            ).fetchone()
            if not result:
                logger.info("为向量表创建 HNSW 索引...")
                conn.execute(
                    f"CREATE INDEX IF NOT EXISTS brianrag_vectors_embedding_idx ON {Config.VECTOR_TABLE_NAME} "
                    "USING hnsw (embedding vector_cosine_ops)"
                )
                conn.commit()
                logger.info("HNSW 索引创建完成")

    def add_documents(self, documents: List[Document]) -> List[str]:
        """批量添加文档（自动生成向量并存储）"""
        return self.vector_store.add_documents(documents)

    def similarity_search(self, query: str, k: int = Config.TOP_K) -> List[Document]:
        """纯向量相似度检索"""
        return self.vector_store.similarity_search(query, k=k)

    def similarity_search_with_score(self, query: str, k: int = Config.TOP_K) -> List[Tuple[Document, float]]:
        """向量检索并返回相似度分数（距离）"""
        return self.vector_store.similarity_search_with_score(query, k=k)