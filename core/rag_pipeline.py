import hashlib
import json
import logging
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)

import jieba  # 用于分词生成高亮词
import redis

from config import Config, config_override
from core.generator import Generator
from core.graph_builder import GraphBuilder

# METRICS: 导入指标记录函数
from core.metrics import (
    record_cache_hit,
    record_cache_miss,
    record_llm_call,
    record_retrieval,
    record_vision_call,
)
from core.query_optimizer import QueryOptimizer
from core.reranker import Reranker
from core.retriever import HybridRetriever
from core.self_correction import SelfCorrector
from utils.hot_question_tracker import record_question

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入智能体函数
try:
    from agentic_graph import run_agent

    AGENTIC_AVAILABLE = True
except ImportError:
    logger.warning("agentic_graph 模块未找到，智能体模式不可用")
    run_agent = None
    AGENTIC_AVAILABLE = False

# 导入图谱工作流
try:
    from core.graph_workflow import app as graph_workflow_app

    GRAPH_WORKFLOW_AVAILABLE = True
except ImportError:
    logger.warning("graph_workflow 模块未找到，图谱工作流模式不可用")
    graph_workflow_app = None
    GRAPH_WORKFLOW_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# 多模态智能体导入
try:
    from core.agents import AgentState, agent_app

    MULTIMODAL_AVAILABLE = True
except ImportError:
    logger.warning("多模态智能体模块未安装，请安装 langgraph")
    MULTIMODAL_AVAILABLE = False
    agent_app = None
    AgentState = None


class RAGPipeline:
    def __init__(self):
        self._retriever = None
        self._graph = None
        self._reranker = None
        self._reranker_model = None
        self._corrector = None
        self._query_optimizer = None
        self.generator = Generator()
        self._model_router = None  # lazy init
        self._init_components()
        # 缓存配置 (使用 Redis db=1)
        from core.redis_client import get_redis

        self.redis_client = get_redis(db=1, decode_responses=True)
        self.cache_ttl = 3600  # 1小时

        # 意图分类器（如果可用）
        try:
            from core.intent_classifier import IntentClassifier

            self.intent_classifier = IntentClassifier()
            logger.info("意图分类器加载成功")
        except ImportError:
            logger.warning("IntentClassifier 模块未找到，将使用基于关键词的简易分类")
            self.intent_classifier = None

    def _classify_intent(self, question: str) -> str:
        """返回意图类型: definition, formula, image, procedure, general"""
        if self.intent_classifier is not None:
            try:
                return self.intent_classifier.classify(question)
            except Exception as e:
                logger.warning(f"意图分类失败: {e}，回退到关键词匹配")
        # 简易关键词匹配
        q_lower = question.lower()
        if any(k in q_lower for k in ["什么是", "定义", "是什么", "含义", "解释"]):
            return "definition"
        if any(k in q_lower for k in ["公式", "参数", "计算", "系数", "数值", "单位"]):
            return "formula"
        if any(k in q_lower for k in ["图片", "图", "图像", "照片", "示意图", "结构图"]):
            return "image"
        if any(k in q_lower for k in ["步骤", "方法", "如何", "怎样", "操作", "流程"]):
            return "procedure"
        return "general"

    def _adjust_params_by_intent(self, intent: str) -> tuple[float, bool]:
        """根据意图返回 (alpha, enable_multimodal)"""
        if intent == "definition":
            return 0.7, False
        elif intent == "formula":
            return 0.3, False
        elif intent == "image":
            return 0.5, True
        elif intent == "procedure":
            return 0.5, False
        else:  # general
            return Config.alpha, Config.enable_multimodal

    def _get_cache_key(self, question: str, history: list = None) -> str:
        """生成缓存键"""
        h = hashlib.md5(question.encode())
        if history:
            hist_str = json.dumps(history[-2:], sort_keys=True)
            h.update(hist_str.encode())
        return f"rag:query:{h.hexdigest()}"

    def _generate_highlight_terms(self, question: str) -> list[str]:
        """生成用于前端高亮的关键词列表"""
        terms = set()
        # 1. 原始问题分词
        for word in jieba.cut(question):
            if len(word) > 1:
                terms.add(word)
        # 2. 改写查询中的词（如果启用）
        if getattr(Config, "ENABLE_QUERY_REWRITE", True):
            rewritten = self.query_optimizer.rewrite_query(question)
            if rewritten and rewritten != question:
                for word in jieba.cut(rewritten):
                    if len(word) > 1:
                        terms.add(word)
        # 3. HyDE 文档中的词（如果启用）
        if getattr(Config, "ENABLE_HYDE", True):
            hyde_doc = self.query_optimizer.hyde_document(question)
            if hyde_doc and hyde_doc != question:
                for word in jieba.cut(hyde_doc):
                    if len(word) > 1:
                        terms.add(word)
        # 按长度降序排序，优先匹配长词
        return sorted(terms, key=len, reverse=True)

    def _init_components(self):
        try:
            self._retriever = HybridRetriever()
            if self._retriever.doc_meta:
                self._retriever.is_loaded = True
            else:
                self._retriever.is_loaded = False
        except Exception as e:
            logger.error(f"初始化 HybridRetriever 失败: {e}")
            self._retriever = None

        if Config.ENABLE_GRAPH:
            try:
                self._graph = GraphBuilder()
                self._graph.load()
            except Exception as e:
                logger.error(f"初始化图谱失败: {e}")
                self._graph = None

        if Config.ENABLE_SELF_CORRECTION:
            try:
                self._corrector = SelfCorrector()
            except Exception as e:
                logger.error(f"初始化自我修正器失败: {e}")
                self._corrector = None

        self._query_optimizer = QueryOptimizer()

    def _get_reranker(self):
        if self._reranker is None and Config.ENABLE_RERANK:
            try:
                self._reranker = Reranker(model_name=Config.RERANK_MODEL, use_fp16=Config.RERANK_USE_FP16)
            except Exception as e:
                logger.error(f"重排序模型加载失败: {e}")
                self._reranker = None
        if self._reranker is not None and not self._reranker.is_available:
            self._reranker = None
        return self._reranker

    @property
    def retriever(self):
        return self._retriever

    @property
    def graph(self):
        return self._graph

    @property
    def reranker(self):
        return self._get_reranker()

    @property
    def corrector(self):
        return self._corrector

    @property
    def query_optimizer(self):
        return self._query_optimizer

    def index_documents(self, file_paths, progress_callback=None, incremental=True):
        if self.retriever is None:
            raise RuntimeError("检索器不可用，无法索引文档。")
        num_chunks = self.retriever.load_documents(
            file_paths, progress_callback=progress_callback, incremental=incremental
        )
        if self.graph and num_chunks > 0:
            self.graph.build_from_chunks(self.retriever.chunks)
            if self.retriever is not None:
                self.retriever.graph_builder = self.graph
                logger.info(f"知识图谱已同步到检索器，节点数: {self.graph.graph.number_of_nodes()}")
        return num_chunks

    @staticmethod
    def _is_similar(a: str, b: str, threshold: float = 0.95) -> bool:
        return SequenceMatcher(None, a, b).ratio() > threshold

    def _enhanced_queries(self, question: str) -> list:
        queries = [question]
        rewrite_enabled = getattr(Config, "ENABLE_QUERY_REWRITE", True)
        hyde_enabled = getattr(Config, "ENABLE_HYDE", True)

        # 使用批量优化：一次 LLM 调用完成 rewrite + HyDE + multi-query
        if rewrite_enabled or hyde_enabled:
            try:
                batch = self.query_optimizer.optimize_batch(question)
                if rewrite_enabled and batch.get("rewritten") and batch["rewritten"] != question:
                    queries.append(batch["rewritten"])
                if hyde_enabled and batch.get("hyde") and batch["hyde"] != question:
                    queries.append(batch["hyde"])
                # 额外变体用于多路检索
                for v in batch.get("variants", []):
                    if v != question and v not in queries:
                        queries.append(v)
            except Exception:
                # 回退到单独调用
                if rewrite_enabled:
                    rewritten = self.query_optimizer.rewrite_query(question)
                    if rewritten and rewritten != question:
                        queries.append(rewritten)
                if hyde_enabled:
                    hyde_doc = self.query_optimizer.hyde_document(question)
                    if hyde_doc and hyde_doc != question:
                        queries.append(hyde_doc)

        if getattr(Config, "ENABLE_SYNONYM_EXPANSION", False):
            expanded = self.query_optimizer.expand_with_synonyms(question)
            if expanded != question:
                queries.append(expanded)
        return queries

    def _multi_query_retrieve(self, queries: list, top_k_per_query: int, alpha: float | None = None):
        if self.retriever is None or not queries:
            return [], []
        if alpha is None:
            from config import _get_config
            alpha = _get_config("alpha")
        all_chunks = []
        all_indices = []
        seen = set()
        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            futures = {executor.submit(self.retriever.hybrid_search, q, top_k_per_query, alpha): q for q in queries}
            for future in futures:
                chunks, indices = future.result()
                for chunk, idx in zip(chunks, indices, strict=False):
                    if chunk not in seen:
                        seen.add(chunk)
                        all_chunks.append(chunk)
                        all_indices.append(idx)
        return all_chunks, all_indices

    def _mmr_reorder(
        self, query: str, chunks: list[str], indices: list[int], lambda_param: float = 0.7, top_k: int = None
    ) -> tuple[list[str], list[int]]:
        """
        使用MMR算法重新排序，平衡相关性与多样性。
        lambda_param: 相关性权重（1-λ为多样性权重），越大越相关，越小越多样。
        top_k: 保留的数量，默认使用 Config.TOP_K
        """
        if top_k is None:
            top_k = Config.TOP_K
        if len(chunks) <= top_k:
            return chunks, indices

        # 尝试导入 sklearn 计算余弦相似度
        try:
            import numpy as _np  # noqa: F401
            from sklearn.metrics.pairwise import cosine_similarity
        except ImportError:
            logger.warning("scikit-learn 未安装，跳过 MMR 重排")
            return chunks[:top_k], indices[:top_k]

        # 批量获取查询向量和块向量（一次 embed 调用）
        try:
            all_embs = self.retriever._sync_embed([query] + chunks)
            query_emb = all_embs[0]
            chunk_embs = all_embs[1:]
            sim_query = cosine_similarity([query_emb], chunk_embs)[0]
            sim_matrix = cosine_similarity(chunk_embs)
        except Exception as e:
            logger.error(f"MMR 向量计算失败: {e}，跳过 MMR 重排")
            return chunks[:top_k], indices[:top_k]

        selected = []
        remaining = list(range(len(chunks)))

        while len(selected) < top_k and remaining:
            mmr_scores = []
            for i in remaining:
                max_sim = max(sim_matrix[i][j] for j in selected) if selected else 0
                mmr = lambda_param * sim_query[i] - (1 - lambda_param) * max_sim
                mmr_scores.append(mmr)
            best_idx = remaining[mmr_scores.index(max(mmr_scores))]
            selected.append(best_idx)
            remaining.remove(best_idx)

        reordered_chunks = [chunks[i] for i in selected]
        reordered_indices = [indices[i] for i in selected]
        return reordered_chunks, reordered_indices

    def _retrieve_and_rerank(self, query, candidate_chunks=None, candidate_indices=None):
        reranked = None  # 用于门控提取重排序分

        if self.retriever is None:
            return [], [], [], [], [], 0.0

        # 第一次检索
        if candidate_chunks is None:
            candidate_count = min(20, Config.TOP_K * Config.RERANK_CANDIDATE_MULTIPLIER)
            candidate_chunks, candidate_indices = self.retriever.hybrid_search(query, top_k=candidate_count)
            if not candidate_chunks:
                return [], [], [], [], [], 0.0

        record_retrieval(mode="candidate", doc_count=len(candidate_chunks))

        # 去重：移除内容高度重复的 chunk，保留首次出现
        if len(candidate_chunks) > 1:
            deduped_chunks = []
            deduped_indices = []
            seen_signatures = set()
            for ck, ci in zip(candidate_chunks, candidate_indices, strict=False):
                sig = hashlib.md5(ck[:80].encode()).hexdigest()
                if sig not in seen_signatures:
                    seen_signatures.add(sig)
                    deduped_chunks.append(ck)
                    deduped_indices.append(ci)
            if len(deduped_chunks) < len(candidate_chunks):
                logger.info(f"去重: {len(candidate_chunks)} → {len(deduped_chunks)} 个候选块")
            candidate_chunks, candidate_indices = deduped_chunks, deduped_indices

        # 重排序
        reranker = self.reranker
        if reranker is not None:
            reranked = reranker.rerank(query, candidate_chunks, top_k=Config.RERANK_TOP_K)
            final_chunks = [text for _, _, text in reranked]
            final_indices = [candidate_indices[idx] for _, idx, _ in reranked]
        else:
            final_chunks = candidate_chunks[: Config.TOP_K]
            final_indices = candidate_indices[: Config.TOP_K]

        # ========== MMR 重排（多样性优化） ==========
        enable_mmr = getattr(Config, "ENABLE_MMR", True)
        if enable_mmr and len(final_chunks) > 1:
            mmr_lambda = getattr(Config, "MMR_LAMBDA", 0.7)
            final_chunks, final_indices = self._mmr_reorder(
                query, final_chunks, final_indices, lambda_param=mmr_lambda, top_k=Config.TOP_K
            )
            logger.info(f"MMR 重排完成，保留 {len(final_chunks)} 个片段")

        record_retrieval(mode="final", doc_count=len(final_chunks))

        # 图谱增强
        extra_indices = []
        if self.graph and Config.ENABLE_GRAPH:
            extra_indices = self.graph.retrieve_by_entities(query, top_k=2)
            extra_indices = list(set(extra_indices))
            extra_chunks = [self.retriever.chunks[i] for i in extra_indices if i < len(self.retriever.chunks)]
            all_chunks = final_chunks.copy()
            for ec in extra_chunks:
                if not any(self._is_similar(ec, existing) for existing in all_chunks):
                    all_chunks.append(ec)
            all_indices = final_indices.copy()
            for idx in extra_indices:
                if idx not in all_indices:
                    all_indices.append(idx)
        else:
            all_chunks = final_chunks
            all_indices = final_indices

        # 自适应二次检索
        if Config.ENABLE_SECONDARY_RETRIEVAL and reranker is not None and "reranked" in locals() and reranked:
            top_score = reranked[0][0] if reranked else 0
            if top_score < Config.SECONDARY_RETRIEVAL_THRESHOLD:
                logger.info(f"最高分 {top_score:.3f} 低于阈值 {Config.SECONDARY_RETRIEVAL_THRESHOLD}，触发二次检索")
                # 策略1: 从候选块提取关键词扩大检索
                keywords = self.retriever.extract_keywords(" ".join(candidate_chunks[:5]))
                new_chunks, new_indices = [], []
                if keywords:
                    new_chunks, new_indices = self.retriever.hybrid_search(keywords, top_k=Config.TOP_K * 3)
                # 策略2: 如果关键词检索仍不足，用原查询扩大范围
                if len(new_chunks) < Config.TOP_K:
                    broader, broader_idx = self.retriever.hybrid_search(query, top_k=Config.TOP_K * 5)
                    new_chunks.extend(broader)
                    new_indices.extend(broader_idx)
                if new_chunks:
                    merged_chunks = candidate_chunks + new_chunks
                    merged_indices = candidate_indices + new_indices
                    unique = {}
                    for c, idx in zip(merged_chunks, merged_indices, strict=False):
                        if c not in unique:
                            unique[c] = idx
                    merged_chunks = list(unique.keys())
                    merged_indices = list(unique.values())
                    reranked_sec = reranker.rerank(query, merged_chunks, top_k=Config.RERANK_TOP_K)
                    final_chunks = [text for _, _, text in reranked_sec]
                    final_indices = [merged_indices[idx] for _, idx, _ in reranked_sec]
                    if enable_mmr:
                        final_chunks, final_indices = self._mmr_reorder(
                            query, final_chunks, final_indices, lambda_param=mmr_lambda, top_k=Config.TOP_K
                        )
                    all_chunks = final_chunks
                    all_indices = final_indices
                    record_retrieval(mode="secondary", doc_count=len(all_chunks))
                else:
                    logger.warning("二次检索未找到新结果")

        # 上下文扩展
        if Config.ENABLE_CONTEXT_EXPANSION and self.retriever:
            all_indices = self.retriever.expand_context(
                all_indices,
                before=getattr(Config, "CONTEXT_EXPANSION_BEFORE", 1),
                after=getattr(Config, "CONTEXT_EXPANSION_AFTER", 1),
            )
            all_chunks = [self.retriever.chunks[i] for i in all_indices if i < len(self.retriever.chunks)]

        # 分离文本块和图片块
        used_images = []
        text_chunks = []
        text_indices = []
        enhanced_chunks = []

        # 虚拟索引映射
        virtual_meta_map = {}
        for ck, ci in zip(candidate_chunks, candidate_indices, strict=False):
            if ci >= len(self.retriever.chunks) and isinstance(ck, str):
                match = re.search(r"!\[.*?\]\((.*?)\)", ck)
                if match:
                    img_url = match.group(1)
                    virtual_meta_map[ci] = {
                        "type": "image",
                        "image_url": img_url,
                        "caption": os.path.basename(img_url),
                        "description": ck,
                    }
                else:
                    virtual_meta_map[ci] = {"type": "image", "caption": "图片", "description": ck}

        for idx, chunk in zip(all_indices, all_chunks, strict=False):
            if idx in virtual_meta_map:
                meta = virtual_meta_map[idx]
            elif idx < len(self.retriever.chunk_metadata):
                meta = self.retriever.chunk_metadata[idx]
            else:
                logger.warning(f"未知索引 {idx}，跳过")
                continue

            if meta.get("type") == "image":
                img_url = meta.get("image_url", "")
                caption = meta.get("caption", meta.get("original_filename", "图片"))
                if img_url:
                    used_images.append({"image_url": img_url, "caption": caption})
                desc = meta.get("description", meta.get("page_content", ""))
                if desc:
                    enhanced_chunks.append(desc)
            else:
                text_chunks.append(chunk)
                text_indices.append(idx)
                enhanced_chunks.append(chunk)

        if not enhanced_chunks and used_images:
            for img in used_images:
                enhanced_chunks.append(f"图片: {img['caption']} (URL: {img['image_url']})")
            logger.info("检测到只有图片检索结果，已将图片描述添加到 LLM 上下文")

        # 获取重排序最高分用于门控判断
        top_rerank_score = reranked[0][0] if reranked else 1.0

        return text_chunks, text_indices, used_images, extra_indices, enhanced_chunks, top_rerank_score

    def _apply_retrieval_gating(
        self, query, text_chunks, text_indices, used_images, extra_indices, llm_context, top_rerank_score
    ):
        """检索门控：质量不达标时触发降级策略，防止低质量上下文导致幻觉"""
        if not getattr(Config, "ENABLE_RETRIEVAL_GATING", False):
            return text_chunks, text_indices, used_images, extra_indices, llm_context, False

        threshold = getattr(Config, "GATING_SCORE_THRESHOLD", 0.25)
        if top_rerank_score >= threshold:
            return text_chunks, text_indices, used_images, extra_indices, llm_context, False

        logger.warning(f"检索质量不达标 (score={top_rerank_score:.3f} < {threshold})，触发降级策略")

        for attempt in range(getattr(Config, "GATING_MAX_RETRIES", 2)):
            if attempt == 0:
                # 策略1：放宽检索范围，用更宽的参数重试
                logger.info("降级策略1/2: 放宽检索范围")
                expanded_chunks, expanded_indices = self.retriever.hybrid_search(query, top_k=Config.TOP_K * 5)
                if expanded_chunks and len(expanded_chunks) >= Config.TOP_K:
                    t, ti, ui, ei, lc, score = self._retrieve_and_rerank(
                        query, candidate_chunks=expanded_chunks, candidate_indices=expanded_indices
                    )
                    if score >= threshold:
                        logger.info(f"放宽检索后达标: score={score:.3f}")
                        return t, ti, ui, ei, lc, False

            elif attempt == 1:
                # 策略2：HyDE 生成假设文档后重新检索
                logger.info("降级策略2/2: HyDE 假设文档检索")
                try:
                    hyde_doc = self.query_optimizer.hyde_document(query)
                    if hyde_doc:
                        hyde_chunks, hyde_indices = self.retriever.hybrid_search(hyde_doc, top_k=Config.TOP_K * 3)
                        if hyde_chunks and len(hyde_chunks) >= Config.TOP_K:
                            t, ti, ui, ei, lc, score = self._retrieve_and_rerank(
                                query, candidate_chunks=hyde_chunks, candidate_indices=hyde_indices
                            )
                            if score >= threshold:
                                logger.info(f"HyDE检索后达标: score={score:.3f}")
                                return t, ti, ui, ei, lc, False
                except Exception as e:
                    logger.warning(f"HyDE降级失败: {e}")

        # 所有降级策略失败 → 标记知识缺口
        logger.warning("所有降级策略失败，标记为知识缺口")
        return text_chunks, text_indices, used_images, extra_indices, llm_context, True

    def _write_cache(self, key: str, result: dict):
        try:
            self.redis_client.setex(key, self.cache_ttl, json.dumps(result, ensure_ascii=False))
            logger.info(f"缓存写入成功: {key}")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")

    def _extract_all_images_from_chunks(self, chunks: list) -> set:
        pattern = r"!\[.*?\]\((.*?)\)"
        images = set()
        for chunk in chunks:
            matches = re.findall(pattern, chunk)
            for img in matches:
                norm = img.replace("\\", "/")
                if not norm.startswith("/images/") and not norm.startswith("http"):
                    norm = f"/images/{os.path.basename(norm)}"
                images.add(norm)
        return images

    def _inject_images_into_answer(self, answer: str, used_chunks: list, used_images: list) -> str:
        image_urls = []
        for img in used_images:
            if isinstance(img, dict):
                url = img.get("image_url")
                if url:
                    image_urls.append(url)
            elif isinstance(img, str):
                image_urls.append(img)
        if not image_urls:
            return answer
        missing = [url for url in image_urls if url not in answer]
        if missing:
            missing_md = "\n\n" + "\n".join([f"![相关图片]({url})" for url in missing])
            answer += missing_md
        return answer

    def _correct_question(self, question: str) -> str:
        """使用小型语言模型进行拼写纠错，返回修正后的问题"""
        try:
            from core.llm_provider import get_small_llm

            llm = get_small_llm()
            prompt = f"""请纠正以下中文问题中的拼写错误、错别字或明显的用词不当，输出修正后的问题。如果没有错误，原样输出。只输出问题本身，不要解释，不要加引号。

原问题：{question}
修正后："""
            corrected = llm.generate(prompt, options={"temperature": 0, "num_predict": 128})
            if corrected and corrected != question:
                logger.info(f"拼写纠错: '{question}' -> '{corrected}'")
                return corrected
        except Exception as e:
            logger.warning(f"拼写纠错失败: {e}")
        return question

    def query(self, question: str, history: list = None) -> dict:
        try:
            record_question(question)
        except Exception as e:
            logger.warning(f"记录热点问题失败: {e}")

        cache_key = self._get_cache_key(question, history)
        cached = self.redis_client.get(cache_key)
        if cached:
            logger.info("命中缓存，直接返回结果")
            record_cache_hit()
            return json.loads(cached)
        else:
            record_cache_miss()

        # 预训练问答缓存检查
        try:
            from core.prewarm import PrewarmEngine

            prewarm = PrewarmEngine(pipeline=self)
            prewarm_hit = prewarm.find_similar(question)
            if prewarm_hit and prewarm_hit.get("answer") and len(prewarm_hit["answer"]) > 20:
                logger.info("命中预训练缓存，快速返回")
                record_cache_hit()
                return {
                    "question": question,
                    "answer": prewarm_hit["answer"],
                    "citations": prewarm_hit.get("citations", {}),
                    "used_chunks": prewarm_hit.get("chunks", []),
                    "used_images": [],
                    "graph_extra_indices": [],
                    "highlight_terms": [],
                    "suggestion": None,
                    "prewarm": True,
                }
        except Exception as e:
            logger.debug(f"预训练缓存检查跳过: {e}")

        # ── Memory 系统: 加载用户记忆上下文 ──
        memory_context = ""
        try:
            from core.memory import get_user_memory
            user_id = history[0].get("user_id", "default") if history else "default"
            memory = get_user_memory(user_id)
            memory_context = memory.relevant_context(question, max_items=8)
        except Exception:
            pass

        if self.retriever is None:
            return self._empty_result(question, error="检索器未初始化")

        intent = self._classify_intent(question)
        logger.info(f"意图分类结果: {intent}")
        dynamic_alpha, enable_multimodal = self._adjust_params_by_intent(intent)

        # 模型智能路由
        if self._model_router is None:
            from core.model_router import ModelRouter
            self._model_router = ModelRouter()
        route_model, _ = self._model_router.route(intent, question)
        if route_model != Config.llm_model:
            logger.info(f"模型路由: {Config.llm_model} → {route_model}")

        suggestion = None

        with config_override(alpha=dynamic_alpha, enable_multimodal=enable_multimodal):
            if intent == "image" and enable_multimodal:
                multimodal_result = self.multimodal_query(question, history)
                if multimodal_result.get("used_images"):
                    return multimodal_result

            # 问题拆解：复合问题拆为子问题分别检索
            sub_queries = self.query_optimizer.decompose_query(question)
            if len(sub_queries) > 1:
                logger.info(f"复合问题拆解为 {len(sub_queries)} 个子问题")
                candidate_chunks, candidate_indices = self._multi_query_retrieve(
                    sub_queries, top_k_per_query=Config.TOP_K
                )
            else:
                queries = self._enhanced_queries(question)
                candidate_chunks, candidate_indices = self._multi_query_retrieve(
                    queries, top_k_per_query=Config.TOP_K * 2
                )
            if not candidate_chunks:
                candidate_chunks, candidate_indices = self.retriever.hybrid_search(question, top_k=Config.TOP_K * 2)

            if not candidate_chunks:
                corrected = self._correct_question(question)
                if corrected != question:
                    suggestion = corrected
                    candidate_chunks, candidate_indices = self.retriever.hybrid_search(
                        corrected, top_k=Config.TOP_K * 2
                    )
                    if candidate_chunks:
                        logger.info(f"使用修正后的问题 '{corrected}' 检索到结果")

            if not candidate_chunks:
                return self._empty_result(question, suggestion=suggestion)

            text_chunks, text_indices, used_images, extra_indices, llm_context, top_rerank_score = (
                self._retrieve_and_rerank(
                    question, candidate_chunks=candidate_chunks, candidate_indices=candidate_indices
                )
            )

            # 检索门控：低质量上下文触发降级或知识缺口
            text_chunks, text_indices, used_images, extra_indices, llm_context, knowledge_gap = (
                self._apply_retrieval_gating(
                    question, text_chunks, text_indices, used_images, extra_indices, llm_context, top_rerank_score
                )
            )
            if knowledge_gap:
                gap_response = getattr(Config, "GATING_KNOWLEDGE_GAP_RESPONSE", "该问题超出当前知识库范围。")
                return self._empty_result(question, suggestion=suggestion, answer=gap_response)

            answer, citations = self.generator.generate(question, llm_context, history=history, model=route_model)

            if self.corrector and Config.ENABLE_SELF_CORRECTION:
                try:
                    answer, citations = self.corrector.correct(
                        question=question,
                        answer=answer,
                        contexts=llm_context,
                        threshold=Config.SELF_CORRECTION_SCORE_THRESHOLD,
                    )
                    logger.info("自我修正已完成")
                except Exception as e:
                    logger.error(f"自我修正失败: {e}")

            record_llm_call(model=Config.LLM_MODEL, operation="generate", prompt_tokens=0, completion_tokens=0)

            answer = self._inject_images_into_answer(answer, text_chunks, used_images)

            highlight_terms = self._generate_highlight_terms(question)

            # 构建 chunk 来源元数据（文件名 + 分数）
            chunk_sources = []
            for i, idx in enumerate(text_indices):
                src = {}
                if self.retriever and idx < len(self.retriever.chunk_metadata):
                    meta = self.retriever.chunk_metadata[idx]
                    source_path = meta.get("source", "")
                    # 提取相对于 data/ 的路径
                    if source_path:
                        src["file"] = source_path.replace("\\", "/").split("/udoc/")[-1].split("/data/")[-1]
                    src["type"] = meta.get("type") or meta.get("source_type", "text")
                src["score"] = round(top_rerank_score, 3) if i == 0 else None
                chunk_sources.append(src)

            # 增强 citations，附加来源信息
            enhanced_citations = {}
            for num_str, chunk_text in citations.items():
                idx = int(num_str) - 1
                enhanced_citations[num_str] = {
                    "text": chunk_text,
                    "source": chunk_sources[idx] if idx < len(chunk_sources) else {},
                }
                if enhanced_citations[num_str]["source"].get("score") is None:
                    enhanced_citations[num_str]["source"]["score"] = round(top_rerank_score, 3)

            result = {
                "question": question,
                "answer": answer,
                "used_chunks": text_chunks,
                "used_images": used_images,
                "citations": enhanced_citations,
                "chunk_sources": chunk_sources,
                "graph_extra_indices": extra_indices,
                "highlight_terms": highlight_terms,
                "suggestion": suggestion,
            }
            self._write_cache(cache_key, result)
            return result

    def query_stream(self, question: str, history: list = None, stop_check=None):
        """
        流式生成答案，支持停止检查。
        stop_check: 可选的回调函数，返回 True 表示应停止生成。
        """
        if self.retriever is None:
            yield "检索器未初始化，无法回答问题。"
            return

        yield '{"__phase__":"searching"}'
        intent = self._classify_intent(question)
        dynamic_alpha, enable_multimodal = self._adjust_params_by_intent(intent)
        suggestion = None

        with config_override(alpha=dynamic_alpha, enable_multimodal=enable_multimodal):
            if intent == "image" and enable_multimodal:
                multimodal_result = self.multimodal_query(question, history)
                if multimodal_result.get("used_images"):
                    yield multimodal_result["answer"]
                    return

            queries = self._enhanced_queries(question)
            candidate_chunks, candidate_indices = self._multi_query_retrieve(queries, top_k_per_query=Config.TOP_K * 2)
            if not candidate_chunks:
                candidate_chunks, candidate_indices = self.retriever.hybrid_search(question, top_k=Config.TOP_K * 2)

            if not candidate_chunks:
                corrected = self._correct_question(question)
                if corrected != question:
                    suggestion = corrected
                    candidate_chunks, candidate_indices = self.retriever.hybrid_search(
                        corrected, top_k=Config.TOP_K * 2
                    )
                    if candidate_chunks:
                        logger.info(f"使用修正后的问题 '{corrected}' 检索到结果")

            if not candidate_chunks:
                yield self._empty_result(question, suggestion=suggestion)["answer"]
                return

            text_chunks, text_indices, used_images, extra_indices, llm_context, top_rerank_score = (
                self._retrieve_and_rerank(
                    question, candidate_chunks=candidate_chunks, candidate_indices=candidate_indices
                )
            )

            # 检索门控
            text_chunks, text_indices, used_images, extra_indices, llm_context, knowledge_gap = (
                self._apply_retrieval_gating(
                    question, text_chunks, text_indices, used_images, extra_indices, llm_context, top_rerank_score
                )
            )
            if knowledge_gap:
                gap_response = getattr(Config, "GATING_KNOWLEDGE_GAP_RESPONSE", "该问题超出当前知识库范围。")
                yield gap_response
                return

            record_retrieval(mode="streaming", doc_count=len(text_chunks))

            yield '{"__phase__":"generating"}'
            answer_generator = self.generator.generate_stream(question, llm_context, history=history)
            full_answer = ""
            for chunk in answer_generator:
                if stop_check and stop_check():
                    break
                full_answer += chunk
                yield chunk

            final_answer = self._inject_images_into_answer(full_answer, text_chunks, used_images)
            record_llm_call(model=Config.LLM_MODEL, operation="generate_stream", prompt_tokens=0, completion_tokens=0)

            citations = self.generator._extract_citations(final_answer, llm_context)
            highlight_terms = self._generate_highlight_terms(question)
            # 构建 chunk 来源信息
            stream_chunk_sources = []
            for i, idx in enumerate(text_indices):
                src = {}
                if self.retriever and idx < len(self.retriever.chunk_metadata):
                    meta = self.retriever.chunk_metadata[idx]
                    sp = meta.get("source", "")
                    if sp:
                        src["file"] = sp.replace("\\", "/").split("/udoc/")[-1].split("/data/")[-1]
                    src["type"] = meta.get("type") or meta.get("source_type", "text")
                src["score"] = round(top_rerank_score, 3) if i == 0 else None
                stream_chunk_sources.append(src)
            # 流式结束前发送元数据
            yield json.dumps({
                "__meta__": True,
                "citations": citations,
                "used_chunks": text_chunks,
                "chunk_sources": stream_chunk_sources,
            }, ensure_ascii=False)

    def agentic_query(self, question: str, history: list = None) -> dict:
        if AGENTIC_AVAILABLE and run_agent is not None:
            try:
                answer = run_agent(question, history=history)
                record_llm_call(model=Config.LLM_MODEL, operation="agentic", prompt_tokens=0, completion_tokens=0)
                return {
                    "question": question,
                    "answer": answer,
                    "used_chunks": [],
                    "used_images": [],
                    "citations": {},
                    "graph_extra_indices": [],
                    "highlight_terms": [],
                    "suggestion": None,
                }
            except Exception as e:
                logger.error(f"智能体执行失败: {e}", exc_info=True)
                return self._empty_result(question, error="智能体调用出错")
        else:
            logger.warning("智能体模块不可用，回退到普通 RAG")
            return self.query(question, history)

    def graph_query(self, question: str, history: list = None) -> dict:
        if GRAPH_WORKFLOW_AVAILABLE and graph_workflow_app is not None:
            try:
                initial_state = {
                    "messages": history or [],
                    "question": question,
                    "current_query": question,
                    "iteration": 0,
                    "candidate_chunks": [],
                    "candidate_indices": [],
                    "final_chunks": [],
                    "final_indices": [],
                    "used_images": [],
                    "answer": "",
                    "citations": {},
                    "need_rewrite": False,
                    "score": 0.0,
                    "metadata": {},
                }
                final_state = graph_workflow_app.invoke(initial_state)
                record_llm_call(
                    model=Config.LLM_MODEL, operation="graph_workflow", prompt_tokens=0, completion_tokens=0
                )
                highlight_terms = self._generate_highlight_terms(question)
                return {
                    "question": question,
                    "answer": final_state.get("answer", "未生成答案"),
                    "used_chunks": final_state.get("final_chunks", []),
                    "used_images": final_state.get("used_images", []),
                    "citations": final_state.get("citations", {}),
                    "graph_extra_indices": final_state.get("metadata", {}).get("extra_indices", []),
                    "highlight_terms": highlight_terms,
                    "suggestion": None,
                }
            except Exception as e:
                logger.error(f"图谱工作流失败: {e}", exc_info=True)
                return self._empty_result(question, error="图谱工作流出错")
        else:
            logger.warning("图谱工作流模块不可用，回退到普通 RAG")
            return self.query(question, history)

    def agentic_multimodal_query(self, question: str, history: list = None) -> dict:
        if not MULTIMODAL_AVAILABLE or agent_app is None:
            logger.warning("多模态智能体不可用，回退到普通查询")
            return self.query(question, history)

        start = time.perf_counter()
        initial_state: AgentState = {
            "question": question,
            "history": history or [],
            "question_type": "text",
            "retrieved_chunks": [],
            "retrieved_images": [],
            "table_data": None,
            "chart_description": None,
            "final_answer": "",
            "citations": {},
            "iteration": 0,
            "metadata": {},
        }
        final_state = agent_app.invoke(initial_state)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"[multi_modal] total cost {elapsed_ms:.2f}ms, question={question[:50]}...")
        record_vision_call()
        record_llm_call(model=Config.LLM_MODEL, operation="multimodal_agent", prompt_tokens=0, completion_tokens=0)
        used_images = []
        for img in final_state.get("retrieved_images", []):
            if isinstance(img, dict):
                used_images.append(img)
            elif isinstance(img, str):
                used_images.append({"image_url": img, "caption": "图片"})
        highlight_terms = self._generate_highlight_terms(question)
        return {
            "question": question,
            "answer": final_state["final_answer"],
            "used_chunks": final_state.get("retrieved_chunks", []),
            "used_images": used_images,
            "citations": final_state.get("citations", {}),
            "graph_extra_indices": [],
            "highlight_terms": highlight_terms,
            "suggestion": None,
        }

    def _empty_result(self, question: str, error: str = "", suggestion: str = None, answer: str = None) -> dict:
        """当没有检索到任何相关内容时，返回友好的提示信息，可附带建议"""
        if answer:
            pass  # 使用传入的预设回复（如知识缺口）
        elif error:
            answer = f"❌ 抱歉，处理您的问题时遇到错误：{error}\n\n请稍后重试或联系管理员。"
        else:
            answer = f"😥 抱歉，在知识库中没有找到与“{question}”直接相关的内容。\n\n"
            if suggestion:
                answer += f"**您是不是想问：** “{suggestion}”？\n\n"
            answer += (
                "**建议您尝试：**\n"
                "1. 换个更具体或更简洁的说法重新提问\n"
                "2. 检查文档是否已成功索引（侧边栏“已索引文档”）\n"
                "3. 如果问题涉及图片，请确保文件夹上传时包含图片文件\n"
                "4. 您可以尝试提问：“有哪些文档？”或列出当前知识库中的文件\n\n"
                "如果问题持续存在，请联系管理员检查索引状态。"
            )
        return {
            "question": question,
            "answer": answer,
            "used_chunks": [],
            "used_images": [],
            "citations": {},
            "graph_extra_indices": [],
            "highlight_terms": [],
            "suggestion": suggestion,
        }

    def multimodal_query(self, query: str, history: list[dict] = None) -> dict:
        if history is None:
            history = []
        if not self.retriever or not self.retriever.clip_retriever:
            logger.warning("多模态检索未启用，回退到普通RAG")
            return self.query(query, history)

        text_contents, text_metas = self.retriever.hybrid_search(query, top_k=Config.TOP_K)
        multimodal_results = self.retriever.multimodal_search(query, top_k=Config.MULTIMODAL_TOP_K)
        multimodal_docs = [doc for doc, _ in multimodal_results]
        multimodal_metas = [doc.metadata for doc, _ in multimodal_results]

        record_vision_call()
        record_retrieval(mode="multimodal", doc_count=len(multimodal_docs))

        all_contents = text_contents + [doc.page_content for doc in multimodal_docs]
        all_metas = text_metas + multimodal_metas

        answer, _ = self.generator.generate(query, all_contents, history=history)

        record_llm_call(model=Config.LLM_MODEL, operation="multimodal_query", prompt_tokens=0, completion_tokens=0)

        used_images = []
        for meta in all_metas:
            if meta.get("type") == "image" or meta.get("image_path"):
                url = meta.get("image_url", "")
                if url:
                    used_images.append({"image_url": url, "caption": meta.get("original_filename", "图片")})

        highlight_terms = self._generate_highlight_terms(query)

        return {
            "answer": answer,
            "used_chunks": text_contents,
            "used_images": used_images,
            "citations": {},
            "graph_extra_indices": [],
            "highlight_terms": highlight_terms,
            "suggestion": None,
        }

    def _build_prompt(self, question: str, context: str, history: list = None) -> str:
        prompt = "你是一个专业的智能助手。基于以下上下文回答问题。\n\n"
        prompt += f"上下文：\n{context}\n\n"
        if history:
            prompt += "对话历史：\n"
            for h in history[-3:]:
                prompt += f"用户：{h.get('content', '')}\n"
        prompt += f"问题：{question}\n\n"
        prompt += "请给出清晰、准确的回答。"
        return prompt
