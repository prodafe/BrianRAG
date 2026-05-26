"""
LangGraph 工作流定义 - BrianRAG 智能检索生成图
"""

import operator
from typing import List, Dict, Any, Optional, TypedDict, Annotated
from langgraph.graph import StateGraph, END
from config import Config
from core.retriever import HybridRetriever
from core.reranker import Reranker
from core.generator import Generator
from core.graph_builder import GraphBuilder
from core.self_correction import SelfCorrector
import logging

logger = logging.getLogger(__name__)
# ---------- 初始化全局组件（复用 pipeline 实例，避免重复加载） ----------
retriever = None
reranker = None
generator = None
graph_builder = None
corrector = None


def ensure_components():
    global retriever, reranker, generator, graph_builder, corrector
    if retriever is None:
        retriever = HybridRetriever()
        # retriever.load()
        if retriever.doc_meta:
            retriever.is_loaded = True
            logger.info("图谱工作流检索器已从已有索引加载")
    if Config.ENABLE_RERANK and reranker is None:
        reranker = Reranker(model_name=Config.RERANK_MODEL, use_fp16=Config.RERANK_USE_FP16)
    if generator is None:
        generator = Generator()
    if Config.ENABLE_GRAPH and graph_builder is None:
        graph_builder = GraphBuilder()
        graph_builder.load()
    if Config.ENABLE_SELF_CORRECTION and corrector is None:
        corrector = SelfCorrector()


# ---------- 状态定义 ----------
class AgentState(TypedDict):
    # 输入输出基本字段
    messages: List[Dict[str, str]]  # 对话历史
    question: str  # 原始问题
    current_query: str  # 当前使用的查询（可能被改写）
    iteration: int  # 当前重试次数

    # 检索与重排序结果
    candidate_chunks: List[str]  # 混合检索原始候选片段
    candidate_indices: List[int]  # 对应索引
    final_chunks: List[str]  # 重排序 / 图谱增强后最终片段
    final_indices: List[int]  # 对应索引
    used_images: List[List[str]]  # 每个片段关联的图片路径

    # 生成与评估
    answer: str  # 当前生成的答案
    citations: Dict[str, str]  # 引用标记 -> 片段内容
    need_rewrite: bool  # 是否需要改写查询
    score: float  # 评估得分

    # 元数据
    metadata: Dict[str, Any]  # 额外信息（如图谱索引等）


# ---------- 节点函数 ----------
def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """检索节点：执行混合检索，获取候选片段"""
    ensure_components()
    query = state["current_query"]
    candidate_count = min(20, Config.TOP_K * Config.RERANK_CANDIDATE_MULTIPLIER)
    chunks, indices = retriever.hybrid_search(query, top_k=candidate_count)
    return {"candidate_chunks": chunks, "candidate_indices": indices}


def rerank_node(state: AgentState) -> Dict[str, Any]:
    """重排序节点：对候选片段重排序，并可选图谱增强"""
    ensure_components()
    query = state["current_query"]
    cand_chunks = state["candidate_chunks"]
    cand_indices = state["candidate_indices"]

    if not cand_chunks:
        return {"final_chunks": [], "final_indices": [], "used_images": []}

    # 重排序
    if reranker is not None:
        reranked = reranker.rerank(query, cand_chunks, top_k=Config.RERANK_TOP_K)
        final_chunks = [text for _, _, text in reranked]
        final_indices = [cand_indices[idx] for _, idx, _ in reranked]
    else:
        final_chunks = cand_chunks[: Config.TOP_K]
        final_indices = cand_indices[: Config.TOP_K]

    # 图谱增强（可选）
    extra_indices = []
    if Config.ENABLE_GRAPH and graph_builder is not None:
        extra_indices = graph_builder.retrieve_by_entities(query, top_k=2)
        extra_indices = list(set(extra_indices))
        extra_chunks = [retriever.chunks[i] for i in extra_indices if i < len(retriever.chunks)]
        # 相似度去重
        from difflib import SequenceMatcher

        def is_similar(a, b, thresh=0.95):
            return SequenceMatcher(None, a, b).ratio() > thresh

        all_chunks = final_chunks.copy()
        for ec in extra_chunks:
            if not any(is_similar(ec, exist) for exist in all_chunks):
                all_chunks.append(ec)
        all_indices = final_indices.copy()
        for idx in extra_indices:
            if idx not in all_indices:
                all_indices.append(idx)
        final_chunks = all_chunks
        final_indices = all_indices

    # 获取关联图片
    used_images = retriever.get_chunk_images(final_indices)

    return {
        "final_chunks": final_chunks,
        "final_indices": final_indices,
        "used_images": used_images,
        "metadata": {"extra_indices": extra_indices},
    }


def generate_node(state: AgentState) -> Dict[str, Any]:
    """生成节点：基于最终片段生成答案"""
    ensure_components()
    query = state["current_query"]
    chunks = state["final_chunks"]
    history = state.get("messages", [])
    answer, citations = generator.generate(query, chunks, history=history)
    return {"answer": answer, "citations": citations}


def evaluate_node(state: AgentState) -> Dict[str, Any]:
    """评估节点：评估答案质量，决定是否需要改写查询"""
    ensure_components()
    if corrector is None:
        return {"need_rewrite": False, "score": 1.0, "iteration": state["iteration"] + 1}

    score = corrector.evaluate_answer(state["question"], state["answer"], state["final_chunks"])
    iteration = state["iteration"] + 1
    need_rewrite = score < Config.SELF_CORRECTION_SCORE_THRESHOLD and iteration <= Config.SELF_CORRECTION_MAX_RETRIES
    return {"need_rewrite": need_rewrite, "score": score, "iteration": iteration}


def rewrite_node(state: AgentState) -> Dict[str, Any]:
    """查询改写节点：生成新的查询字符串"""
    ensure_components()
    new_query = corrector.rewrite_query(state["question"]) if corrector else state["question"]
    return {"current_query": new_query}


# ---------- 条件边函数 ----------
def should_continue(state: AgentState) -> str:
    """条件判断：是否继续重试改写"""
    if state.get("need_rewrite", False):
        return "rewrite"
    else:
        return "end"


# ---------- 构建图 ----------
def build_graph() -> StateGraph:
    ensure_components()
    workflow = StateGraph(AgentState)

    # 添加节点
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("rerank", rerank_node)
    workflow.add_node("generate", generate_node)
    workflow.add_node("evaluate", evaluate_node)
    workflow.add_node("rewrite", rewrite_node)

    # 设置入口
    workflow.set_entry_point("retrieve")

    # 添加边
    workflow.add_edge("retrieve", "rerank")
    workflow.add_edge("rerank", "generate")
    workflow.add_edge("generate", "evaluate")
    workflow.add_conditional_edges("evaluate", should_continue, {"rewrite": "rewrite", "end": END})
    workflow.add_edge("rewrite", "retrieve")

    return workflow.compile()


# ---------- 导出可运行实例 ----------
app = build_graph()
