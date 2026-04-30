from core.retriever import HybridRetriever
from core.generator import Generator
from core.graph_builder import GraphBuilder
from core.reranker import Reranker
from config import Config
from difflib import SequenceMatcher
import queue
import threading
from core.self_correction import SelfCorrector
import time
import logging
from core.query_optimizer import QueryOptimizer
import sys
import os
from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import redis
import re
import streamlit as st

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# 导入智能体函数
try:
    from agentic_graph import run_agent

    AGENTIC_AVAILABLE = True
except ImportError:
    print("警告: agentic_graph 模块未找到，智能体模式不可用")
    run_agent = None
    AGENTIC_AVAILABLE = False

# 导入图谱工作流
try:
    from core.graph_workflow import app as graph_workflow_app

    GRAPH_WORKFLOW_AVAILABLE = True
except ImportError:
    print("警告: graph_workflow 模块未找到，图谱工作流模式不可用")
    graph_workflow_app = None
    GRAPH_WORKFLOW_AVAILABLE = False

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# 多模态智能体导入
try:
    from core.agents.workflow import agent_app, AgentState

    MULTIMODAL_AVAILABLE = True
except ImportError:
    print("警告: 多模态智能体模块未安装，请安装 langgraph 并创建 core/agents 文件")
    MULTIMODAL_AVAILABLE = False
    agent_app = None
    AgentState = None


class RAGPipeline:
    def __init__(self):
        self._retriever = None
        self._graph = None
        self._reranker = None  # 延迟加载
        self._reranker_model = None  # 存储配置，首次使用时加载
        self._corrector = None
        self._query_optimizer = None
        self.generator = Generator()
        self._init_components()
        # 缓存配置 (使用 Redis db=1)
        self.redis_client = redis.Redis(host='localhost', port=6379, db=1, decode_responses=True)
        self.cache_ttl = 3600  # 1小时

    def _get_cache_key(self, question: str, history: list = None) -> str:
        """生成缓存键"""
        h = hashlib.md5(question.encode())
        if history:
            # 只取最近两轮对话作为上下文
            hist_str = json.dumps(history[-2:], sort_keys=True)
            h.update(hist_str.encode())
        return f"rag:query:{h.hexdigest()}"

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
        """延迟加载重排序模型"""
        if self._reranker is None and Config.ENABLE_RERANK:
            try:
                self._reranker = Reranker(model_name=Config.RERANK_MODEL, use_fp16=Config.RERANK_USE_FP16)
                logger.info("重排序模型延迟加载成功")
            except Exception as e:
                logger.error(f"重排序模型加载失败: {e}")
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
        num_chunks = self.retriever.load_documents(file_paths, progress_callback=progress_callback,
                                                   incremental=incremental)
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
        if getattr(Config, 'ENABLE_QUERY_REWRITE', True):
            rewritten = self.query_optimizer.rewrite_query(question)
            if rewritten and rewritten != question:
                queries.append(rewritten)
        if getattr(Config, 'ENABLE_HYDE', True):
            hyde_doc = self.query_optimizer.hyde_document(question)
            if hyde_doc and hyde_doc != question:
                queries.append(hyde_doc)
        return queries

    def _multi_query_retrieve(self, queries: list, top_k_per_query: int):
        if self.retriever is None or not queries:
            return [], []
        all_chunks = []
        all_indices = []
        seen = set()
        with ThreadPoolExecutor(max_workers=len(queries)) as executor:
            futures = {executor.submit(self.retriever.hybrid_search, q, top_k_per_query): q for q in queries}
            for future in futures:
                chunks, indices = future.result()
                for chunk, idx in zip(chunks, indices):
                    if chunk not in seen:
                        seen.add(chunk)
                        all_chunks.append(chunk)
                        all_indices.append(idx)
        return all_chunks, all_indices

    def _retrieve_and_rerank(self, query, candidate_chunks=None, candidate_indices=None):
        if self.retriever is None:
            return [], [], [], []

        # 第一次检索
        if candidate_chunks is None:
            candidate_count = min(20, Config.TOP_K * Config.RERANK_CANDIDATE_MULTIPLIER)
            candidate_chunks, candidate_indices = self.retriever.hybrid_search(query, top_k=candidate_count)
            if not candidate_chunks:
                return [], [], [], []

        # 重排序（使用延迟加载的 reranker）
        reranker = self.reranker  # 触发延迟加载
        if reranker is not None:
            reranked = reranker.rerank(query, candidate_chunks, top_k=Config.RERANK_TOP_K)
            final_chunks = [text for _, _, text in reranked]
            final_indices = [candidate_indices[idx] for _, idx, _ in reranked]
        else:
            final_chunks = candidate_chunks[:Config.TOP_K]
            final_indices = candidate_indices[:Config.TOP_K]

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

        # 二次检索（当最高分低于阈值时）
        if Config.ENABLE_SECONDARY_RETRIEVAL and reranker is not None and 'reranked' in locals() and reranked:
            top_score = reranked[0][0] if reranked else 0
            if top_score < Config.SECONDARY_RETRIEVAL_THRESHOLD:
                logger.info(f"最高分 {top_score:.3f} 低于阈值 {Config.SECONDARY_RETRIEVAL_THRESHOLD}，触发二次检索")
                keywords = self.retriever.extract_keywords(" ".join(candidate_chunks[:5]))
                if keywords:
                    new_chunks, new_indices = self.retriever.hybrid_search(keywords, top_k=Config.TOP_K * 2)
                    if new_chunks:
                        merged_chunks = candidate_chunks + new_chunks
                        merged_indices = candidate_indices + new_indices
                        unique = {}
                        for c, idx in zip(merged_chunks, merged_indices):
                            if c not in unique:
                                unique[c] = idx
                        merged_chunks = list(unique.keys())
                        merged_indices = list(unique.values())
                        reranked_sec = reranker.rerank(query, merged_chunks, top_k=Config.RERANK_TOP_K)
                        final_chunks = [text for _, _, text in reranked_sec]
                        final_indices = [merged_indices[idx] for _, idx, _ in reranked_sec]
                        all_chunks = final_chunks
                        all_indices = final_indices

        # 上下文扩展
        if Config.ENABLE_CONTEXT_EXPANSION and self.retriever:
            all_indices = self.retriever.expand_context(
                all_indices,
                before=getattr(Config, 'CONTEXT_EXPANSION_BEFORE', 1),
                after=getattr(Config, 'CONTEXT_EXPANSION_AFTER', 1)
            )
            all_chunks = [self.retriever.chunks[i] for i in all_indices if i < len(self.retriever.chunks)]

        used_images = self.retriever.get_chunk_images(all_indices)

        # --- 为每个文本块附加对应的图片 Markdown（增强上下文）---
        enhanced_chunks = []
        for idx, chunk in zip(all_indices, all_chunks):
            img_paths = self.retriever.chunk_images[idx] if idx < len(self.retriever.chunk_images) else []
            img_markdown = "\n".join([f"![{os.path.basename(p)}]({p})" for p in img_paths if os.path.exists(p)])
            if img_markdown:
                enhanced_chunk = f"{chunk}\n\n{img_markdown}"
            else:
                enhanced_chunk = chunk
            enhanced_chunks.append(enhanced_chunk)
        return enhanced_chunks, all_indices, used_images, extra_indices

    def _write_cache(self, key: str, result: dict):
        """写入缓存"""
        try:
            self.redis_client.setex(key, self.cache_ttl, json.dumps(result, ensure_ascii=False))
            logger.info(f"缓存写入成功: {key}")
        except Exception as e:
            logger.warning(f"缓存写入失败: {e}")

    def _inject_images_into_answer(self, answer: str, used_chunks: list, used_images: list) -> str:
        """在答案中每个引用编号后面插入对应的图片缩略图（HTML）"""
        # 构建编号到图片的映射（取每个 chunk 的第一张图）
        index_to_image = {}
        for i, img_list in enumerate(used_images):
            if img_list:
                # 只取第一张图
                img_path = img_list[0]
                # 转换为可访问的 URL（假设静态路由 /images）
                img_url = f"/images/{os.path.basename(img_path)}"
                index_to_image[i + 1] = img_url

        def replacer(match):
            num = int(match.group(1))
            if num in index_to_image:
                img_url = index_to_image[num]
                # 插入缩略图样式
                return f"{match.group(0)}<br><img src='{img_url}' width='200' style='margin:5px; border-radius:5px; cursor:pointer;' onclick=\"window.open('{img_url}')\">"
            return match.group(0)

        # 使用正则替换 [数字]
        new_answer = re.sub(r'\[(\d+)\]', replacer, answer)
        return new_answer

    def query(self, question: str, history: list = None) -> dict:
        """普通同步查询（支持缓存）"""
        cache_key = self._get_cache_key(question, history)
        cached = self.redis_client.get(cache_key)
        if cached:
            logger.info("命中缓存，直接返回结果")
            return json.loads(cached)

        print(f"[DEBUG] query 收到问题: {question}")
        if self.retriever is None:
            return self._empty_result(question, error="检索器未初始化")

        queries = self._enhanced_queries(question)
        candidate_chunks, candidate_indices = self._multi_query_retrieve(queries, top_k_per_query=Config.TOP_K * 2)
        if not candidate_chunks:
            candidate_chunks, candidate_indices = self.retriever.hybrid_search(question, top_k=Config.TOP_K * 2)
        if not candidate_chunks:
            return self._empty_result(question)

        all_chunks, all_indices, used_images, extra_indices = self._retrieve_and_rerank(
            question, candidate_chunks=candidate_chunks, candidate_indices=candidate_indices
        )

        if self.corrector is None:
            answer, citations = self.generator.generate(question, all_chunks, history=history)
        else:
            answer, citations = self.generator.generate(question, all_chunks, history=history)

        # 后处理：将答案中的引用编号替换为图片缩略图
        answer = self._inject_images_into_answer(answer, all_chunks, used_images)

        result = {
            "question": question,
            "answer": answer,
            "used_chunks": all_chunks,
            "used_images": used_images,
            "citations": citations,
            "graph_extra_indices": extra_indices
        }
        self._write_cache(cache_key, result)
        return result

    def query_stream(self, question: str, history: list = None):
        """流式查询，逐词输出答案（最后不输出字典）"""
        if self.retriever is None:
            yield "检索器未初始化，无法回答问题。"
            return

        queries = self._enhanced_queries(question)
        candidate_chunks, candidate_indices = self._multi_query_retrieve(queries, top_k_per_query=Config.TOP_K * 2)
        if not candidate_chunks:
            candidate_chunks, candidate_indices = self.retriever.hybrid_search(question, top_k=Config.TOP_K * 2)
        if not candidate_chunks:
            yield "未找到相关信息。"
            return

        all_chunks, all_indices, used_images, extra_indices = self._retrieve_and_rerank(
            question, candidate_chunks=candidate_chunks, candidate_indices=candidate_indices
        )

        # 流式生成答案
        answer_generator = self.generator.generate_stream(question, all_chunks, history=history)
        full_answer = ""
        for chunk in answer_generator:
            full_answer += chunk
            yield chunk

        # 后处理：将完整答案中的引用编号替换为图片缩略图（但不能在流式过程中做）
        # 由于流式已经结束，无法修改已输出内容，所以图片无法动态插入。
        # 解决方案：将图片信息存入 session_state，前端在流式结束后再渲染图片。
        # 这里我们存入 st.session_state，供前端使用。
        st.session_state.last_rag_result = {
            "used_chunks": all_chunks,
            "used_images": used_images,
            "citations": {},
            "graph_extra_indices": extra_indices,
            "full_answer": full_answer
        }
        # 注意：图片注入需要在前端完成（展示时调用 _inject_images_into_answer 并重新渲染）
        # 为了简化，可以在前端显示图片画廊（已有的 display_images 函数）

    def agentic_query(self, question: str, history: list = None) -> dict:
        if AGENTIC_AVAILABLE and run_agent is not None:
            try:
                answer = run_agent(question, history=history)
                return {
                    "question": question,
                    "answer": answer,
                    "used_chunks": [],
                    "used_images": [],
                    "citations": {},
                    "graph_extra_indices": []
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
                    "metadata": {}
                }
                final_state = graph_workflow_app.invoke(initial_state)
                return {
                    "question": question,
                    "answer": final_state.get("answer", "未生成答案"),
                    "used_chunks": final_state.get("final_chunks", []),
                    "used_images": final_state.get("used_images", []),
                    "citations": final_state.get("citations", {}),
                    "graph_extra_indices": final_state.get("metadata", {}).get("extra_indices", [])
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
            "metadata": {}
        }
        final_state = agent_app.invoke(initial_state)
        elapsed_ms = (time.perf_counter() - start) * 1000
        logger.info(f"[multi_modal] total cost {elapsed_ms:.2f}ms, question={question[:50]}...")
        return {
            "question": question,
            "answer": final_state["final_answer"],
            "used_chunks": final_state.get("retrieved_chunks", []),
            "used_images": final_state.get("retrieved_images", []),
            "citations": final_state.get("citations", {}),
            "graph_extra_indices": []
        }

    def _empty_result(self, question: str, error: str = "") -> dict:
        answer = "未找到相关信息。" + (f" ({error})" if error else "")
        return {
            "question": question,
            "answer": answer,
            "used_chunks": [],
            "used_images": [],
            "citations": {},
            "graph_extra_indices": []
        }

    def start_indexing(self, file_paths, incremental=True, progress_queue=None):
        from tasks import index_documents_task
        result = index_documents_task.delay(file_paths, incremental)
        return result.id