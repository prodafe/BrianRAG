import pickle
import numpy as np
import faiss
import ollama
import os
from config import Config   # 引入配置

class SemanticCache:
    def __init__(self, cache_dir="./cache", threshold=0.95):
        self.dim = Config.EMBEDDING_DIM          # 1024 (bge-m3)
        self.cache_dir = cache_dir
        self.threshold = threshold
        os.makedirs(cache_dir, exist_ok=True)
        self.index = None
        self.questions = []
        self.answers = []

    def _embed(self, text: str) -> np.ndarray:
        """使用 Ollama bge-m3 生成查询向量"""
        response = ollama.embed(model=Config.EMBEDDING_MODEL, input=[text])
        return np.array(response['embeddings'][0]).astype(np.float32).reshape(1, -1)

    def load(self):
        index_path = os.path.join(self.cache_dir, "cache_index.faiss")
        qa_path = os.path.join(self.cache_dir, "qa.pkl")
        if os.path.exists(index_path) and os.path.exists(qa_path):
            self.index = faiss.read_index(index_path)
            with open(qa_path, "rb") as f:
                self.questions, self.answers = pickle.load(f)
            return True
        return False

    def save(self):
        if self.index is None:
            return
        faiss.write_index(self.index, os.path.join(self.cache_dir, "cache_index.faiss"))
        with open(os.path.join(self.cache_dir, "qa.pkl"), "wb") as f:
            pickle.dump((self.questions, self.answers), f)

    def get(self, query: str):
        if self.index is None or self.index.ntotal == 0:
            return None
        q_emb = self._embed(query)
        distances, indices = self.index.search(q_emb, 1)
        # FAISS L2 距离越小越相似，距离 < (1 - threshold) 时视为命中
        if distances[0][0] < (1 - self.threshold):
            return self.answers[indices[0][0]]
        return None

    def put(self, query: str, answer: str):
        if self.index is None:
            self.index = faiss.IndexFlatL2(self.dim)
        q_emb = self._embed(query)
        self.index.add(q_emb)
        self.questions.append(query)
        self.answers.append(answer)
        self.save()