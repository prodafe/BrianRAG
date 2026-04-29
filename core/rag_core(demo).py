import os
import pickle

import jieba
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
from rank_bm25 import BM25Okapi
from langchain_community.document_loaders import TextLoader, PyPDFLoader
from langchain_classic.text_splitter import RecursiveCharacterTextSplitter
import ollama


class TinyRAG:
    def __init__(self, embed_model_name="all-MiniLM-L6-v2"):
        self.embedder = SentenceTransformer(embed_model_name)
        self.dim = self.embedder.get_sentence_embedding_dimension()
        self.index = None
        self.chunks = []  # 原始文本块
        self.bm25 = None
        self.working_dir = "./tinyrag_data"
        os.makedirs(self.working_dir, exist_ok=True)

    def load_documents(self, file_paths):
        """加载并切分文档"""
        all_docs = []
        for path in file_paths:
            if path.endswith(".pdf"):
                loader = PyPDFLoader(path)
            else:
                loader = TextLoader(path, encoding="utf-8")
            all_docs.extend(loader.load())
        splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
        self.chunks = splitter.split_documents(all_docs)
        self.chunks = [chunk.page_content for chunk in self.chunks]
        # 构建 BM25
        tokenized_chunks = [list(jieba.cut(chunk)) for chunk in self.chunks]
        self.bm25 = BM25Okapi(tokenized_chunks)
        # 构建 FAISS 索引
        embeddings = self.embedder.encode(self.chunks, show_progress_bar=True)
        self.index = faiss.IndexFlatL2(self.dim)
        self.index.add(embeddings.astype(np.float32))
        # 保存到磁盘
        self.save()

    def hybrid_search(self, query, top_k=5, alpha=0.5):
        """混合检索：alpha 控制 BM25 与向量的权重"""
        # 向量检索
        q_emb = self.embedder.encode([query])
        distances, indices = self.index.search(q_emb.astype(np.float32), top_k * 2)
        vector_scores = -distances[0]  # L2 距离越小越相关
        # BM25 检索
        tokenized_query = list(jieba.cut(query))
        bm25_scores = self.bm25.get_scores(tokenized_query)
        # 合并排序
        combined = []
        for i, chunk in enumerate(self.chunks):
            v_score = vector_scores[i] if i in indices[0] else 0
            b_score = bm25_scores[i]
            combined.append((v_score * alpha + b_score * (1 - alpha), i))
        combined.sort(reverse=True, key=lambda x: x[0])
        top_indices = [idx for _, idx in combined[:top_k]]
        return [self.chunks[i] for i in top_indices]

    def generate(self, query, context_chunks):
        context = "\n\n".join(context_chunks)
        prompt = f"""基于以下信息回答问题。如果信息不足，请说“根据现有资料无法回答”。
信息：
{context}
问题：{query}
答案："""
        response = ollama.chat(model="mistral-nemo:latest", messages=[{"role": "user", "content": prompt}])
        return response["message"]["content"]

    def save(self):
        with open(os.path.join(self.working_dir, "chunks.pkl"), "wb") as f:
            pickle.dump(self.chunks, f)
        faiss.write_index(self.index, os.path.join(self.working_dir, "faiss.index"))
        with open(os.path.join(self.working_dir, "bm25.pkl"), "wb") as f:
            pickle.dump(self.bm25, f)

    def load(self):
        with open(os.path.join(self.working_dir, "chunks.pkl"), "rb") as f:
            self.chunks = pickle.load(f)
        self.index = faiss.read_index(os.path.join(self.working_dir, "faiss.index"))
        with open(os.path.join(self.working_dir, "bm25.pkl"), "rb") as f:
            self.bm25 = pickle.load(f)