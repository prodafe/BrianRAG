"""RAG 预训练缓存系统 — 基于文档内容预生成问答对并缓存"""

import json
import logging
import time

import numpy as np
import redis

from config import Config

logger = logging.getLogger(__name__)

PREWARM_KEY = "prewarm:qa"
PREWARM_EMB_KEY = "prewarm:emb"


class PrewarmEngine:
    def __init__(self, pipeline=None):
        self.pipeline = pipeline
        self._redis_available = False
        try:
            self.redis = redis.Redis(
                host="localhost", port=6379, db=3, decode_responses=False, socket_connect_timeout=2
            )
            self.emb_redis = redis.Redis(
                host="localhost", port=6379, db=3, decode_responses=True, socket_connect_timeout=2
            )
            self.redis.ping()
            self._redis_available = True
        except Exception:
            logger.warning("Redis db=3 不可用，预训练缓存将仅存于内存")
            self.redis = None
            self.emb_redis = None
        self.target_count = getattr(Config, "PREWARM_QUESTION_COUNT", 150)
        self.similarity_threshold = getattr(Config, "PREWARM_SIMILARITY_THRESHOLD", 0.88)
        self._memory_cache = []
        self._memory_embeddings = []

    def generate_questions_from_chunks(self, chunks: list[str], count: int = 150) -> list[str]:
        """基于文档内容用 LLM 生成可能的问题"""
        all_questions = []
        # 先筛选长文本，再均匀采样
        long_chunks = [c for c in chunks if len(c) >= 50]
        step = max(1, len(long_chunks) // 40)
        sampled = long_chunks[::step][:40]
        logger.info(f"从 {len(chunks)} chunks 筛选出 {len(long_chunks)} 个长文本，采样 {len(sampled)} 个")

        for i, chunk in enumerate(sampled):
            if len(all_questions) >= count:
                break
            if len(chunk) < 30:
                continue

            prompt = f"""你是一个用户，正在使用知识库问答系统。基于以下文档内容，列出 8-10 个你可能会问的具体问题。问题必须基于文档内容，覆盖关键信息。每行一个问题，不要编号。

文档内容：
{chunk[:800]}

你会问的问题："""

            try:
                from core.llm_provider import get_llm_provider

                llm = get_llm_provider()
                resp_text = llm.generate(prompt, options={"temperature": 0.8, "num_predict": 800})
                lines = [l.strip() for l in resp_text.split("\n") if l.strip()]
                # 宽松筛选：只要长度合理就接受
                questions = [l for l in lines if len(l) > 6 and len(l) < 200]
                all_questions.extend(questions)
                logger.info(f"Chunk {i + 1}/{len(sampled)}: {len(questions)} questions (total {len(all_questions)})")
            except Exception as e:
                logger.warning(f"问题生成失败 (chunk {i}): {e}")

        # 去重
        seen = set()
        unique = []
        for q in all_questions:
            key = q[:30]
            if key not in seen:
                seen.add(key)
                unique.append(q)
        logger.info(f"去重后: {len(unique)} 个问题")
        return unique[:count]

    def precompute_answers(self, questions: list[str], progress_cb=None) -> list[dict]:
        """对所有问题预计算答案"""
        if self.pipeline is None:
            from core.rag_pipeline import RAGPipeline

            self.pipeline = RAGPipeline()

        results = []
        total = len(questions)
        for i, q in enumerate(questions):
            try:
                result = self.pipeline.query(q, history=None)
                answer = result.get("answer", "")
                citations = result.get("citations", {})
                chunks_used = result.get("used_chunks", [])
                entry = {
                    "question": q,
                    "answer": answer,
                    "citations": citations,
                    "chunks": chunks_used,
                    "timestamp": time.time(),
                }
                results.append(entry)
                logger.info(f"预计算 [{i + 1}/{total}]: {q[:40]}... → {len(answer)} chars")
            except Exception as e:
                logger.error(f"预计算失败 [{i + 1}/{total}]: {e}")

            if progress_cb:
                progress_cb((i + 1) / total)

        return results

    def store_results(self, results: list[dict]):
        """存储问答对到 Redis 或内存"""
        # 始终保存到内存缓存
        self._memory_cache = results
        self._memory_embeddings = []

        if self._redis_available and self.redis:
            try:
                pipe = self.redis.pipeline()
                for i, entry in enumerate(results):
                    key = f"{PREWARM_KEY}:{i}"
                    pipe.set(key, json.dumps(entry, ensure_ascii=False).encode("utf-8"))
                    pipe.expire(key, Config.HOT_QUESTION_TTL)
                pipe.execute()
                self.redis.set(f"{PREWARM_KEY}:count", str(len(results)))
                self.redis.set(f"{PREWARM_KEY}:updated", str(time.time()))
                logger.info(f"已存储 {len(results)} 个预计算问答对到 Redis")
            except Exception as e:
                logger.warning(f"Redis 存储失败，使用内存缓存: {e}")

        # 为每个问题生成嵌入向量
        try:
            embeddings = []
            batch_size = 16
            from core.llm_provider import get_embed_provider

            emb_provider = get_embed_provider()
            for i in range(0, len(results), batch_size):
                batch = [r["question"] for r in results[i : i + batch_size]]
                embeddings.extend(emb_provider.embed(batch))

            self._memory_embeddings = [np.array(e, dtype=np.float32) for e in embeddings]

            if self._redis_available and self.redis:
                for i, emb in enumerate(embeddings):
                    key = f"{PREWARM_EMB_KEY}:{i}"
                    self.redis.set(key, np.array(emb, dtype=np.float32).tobytes())
            logger.info(f"已生成 {len(embeddings)} 个嵌入向量")
        except Exception as e:
            logger.warning(f"嵌入向量生成失败: {e}")

    def find_similar(self, query: str) -> dict | None:
        """查找与用户问题最相似的预计算答案（优先 Redis，回退内存）"""
        if not self._memory_cache and not (self._redis_available and self.redis):
            return None

        try:
            from core.llm_provider import get_embed_provider

            query_emb = np.array(get_embed_provider().embed_query(query), dtype=np.float32)

            # 优先使用内存中的嵌入
            if self._memory_embeddings:
                best_score = -1
                best_idx = -1
                for i, cached_emb in enumerate(self._memory_embeddings):
                    score = np.dot(query_emb, cached_emb) / (
                        np.linalg.norm(query_emb) * np.linalg.norm(cached_emb) + 1e-8
                    )
                    if score > best_score:
                        best_score = score
                        best_idx = i
                if best_score >= self.similarity_threshold and best_idx >= 0 and best_idx < len(self._memory_cache):
                    entry = self._memory_cache[best_idx]
                    logger.info(f"命中预训练缓存(内存): [{best_idx}] 相似度={best_score:.4f}")
                    return entry

            # 回退到 Redis
            if self._redis_available and self.redis:
                count_str = self.redis.get(f"{PREWARM_KEY}:count")
                if count_str:
                    best_score = -1
                    best_idx = -1
                    for i in range(int(count_str)):
                        emb_bytes = self.redis.get(f"{PREWARM_EMB_KEY}:{i}")
                        if not emb_bytes:
                            continue
                        cached_emb = np.frombuffer(emb_bytes, dtype=np.float32)
                        score = np.dot(query_emb, cached_emb) / (
                            np.linalg.norm(query_emb) * np.linalg.norm(cached_emb) + 1e-8
                        )
                        if score > best_score:
                            best_score = score
                            best_idx = i
                    if best_score >= self.similarity_threshold and best_idx >= 0:
                        data = self.redis.get(f"{PREWARM_KEY}:{best_idx}")
                        if data:
                            entry = json.loads(data.decode("utf-8"))
                            logger.info(f"命中预训练缓存(Redis): [{best_idx}] 相似度={best_score:.4f}")
                            return entry
        except Exception as e:
            logger.warning(f"预训练缓存查询失败: {e}")

        return None

    def run(self, progress_cb=None) -> int:
        """执行完整的预训练流程"""
        if self.pipeline is None:
            from core.rag_pipeline import RAGPipeline

            self.pipeline = RAGPipeline()

        retriever = self.pipeline.retriever
        if retriever is None or not retriever.chunks:
            logger.warning("无可用 chunks，跳过预训练")
            return 0

        logger.info(f"开始预训练: {len(retriever.chunks)} chunks → 目标 {self.target_count} 个问题")

        # Step 1: 生成问题
        questions = self.generate_questions_from_chunks(retriever.chunks, self.target_count)
        if not questions:
            logger.warning("未能生成任何问题")
            return 0

        # Step 2: 预计算答案
        results = self.precompute_answers(questions, progress_cb)
        if not results:
            return 0

        # Step 3: 存储
        self.store_results(results)

        logger.info(f"预训练完成: {len(results)} 个问答对已缓存")
        return len(results)

    def get_status(self) -> dict:
        """获取预训练状态"""
        count = len(self._memory_cache)
        if self._redis_available and self.redis:
            try:
                c = self.redis.get(f"{PREWARM_KEY}:count")
                if c:
                    count = max(count, int(c))
            except:
                pass
        return {"cached_qa_pairs": count, "target_count": self.target_count, "redis_available": self._redis_available}


def run_prewarm():
    """独立运行预训练"""
    engine = PrewarmEngine()
    return engine.run()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    count = run_prewarm()
    logger.info(f"预训练完成: {count} 个问答对")
