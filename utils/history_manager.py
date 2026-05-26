import hashlib
from datetime import datetime
from sqlalchemy import create_engine, Column, String, DateTime, Integer
from sqlalchemy.orm import declarative_base, sessionmaker
from pgvector.sqlalchemy import Vector
from config import Config
from core.retriever import OllamaEmbeddings

Base = declarative_base()


class HistoryQuestion(Base):
    __tablename__ = "history_questions"
    id = Column(String(32), primary_key=True)  # MD5哈希
    question = Column(String(500), nullable=False)
    embedding = Column(Vector(Config.EMBEDDING_DIM))  # 向量维度
    created_at = Column(DateTime, default=datetime.now)
    frequency = Column(Integer, default=1)  # 出现次数


class HistoryManager:
    def __init__(self):
        sync_db_url = Config.DATABASE_URL.replace("postgresql://", "postgresql+psycopg://")
        self.engine = create_engine(sync_db_url)
        # 自动创建表（如果不存在）
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)
        self.embeddings = OllamaEmbeddings(Config.EMBEDDING_MODEL, Config.EMBEDDING_DIM)

    def add_question(self, question: str):
        """记录用户提问，去重并增加频率"""
        q_hash = hashlib.md5(question.encode()).hexdigest()
        sess = self.Session()
        existing = sess.query(HistoryQuestion).filter_by(id=q_hash).first()
        if existing:
            existing.frequency += 1
            existing.created_at = datetime.now()
        else:
            emb = self.embeddings.embed_query(question)
            sess.add(HistoryQuestion(id=q_hash, question=question, embedding=emb))
        sess.commit()
        sess.close()

    def recommend(self, question: str, top_k: int = 3) -> list:
        """返回与当前问题最相似的 top_k 个历史问题（排除自身）"""
        q_emb = self.embeddings.embed_query(question)
        q_hash = hashlib.md5(question.encode()).hexdigest()
        sess = self.Session()
        # 使用余弦距离排序（距离越小越相似）
        results = (
            sess.query(HistoryQuestion)
            .filter(HistoryQuestion.id != q_hash)
            .order_by(HistoryQuestion.embedding.cosine_distance(q_emb))
            .limit(top_k)
            .all()
        )
        sess.close()
        return [r.question for r in results]
