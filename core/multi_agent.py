"""多 Agent 协作系统 — Planner/Retriever/Critic/ReAct 四角色编排 + 工具链

Planner:   分析问题 → 分层任务分解 → 检索计划
Retriever: 执行检索 → 收集证据 → 结构化上下文
ReAct:     思考-行动-观察循环 → 工具链推理 (NEW)
Critic:    验证答案 → 事实准确性 → 循环至达标
"""

from __future__ import annotations

import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    role: str  # planner / retriever / critic / user / react
    content: str
    metadata: dict = field(default_factory=dict)


class MultiAgentOrchestrator:
    """多 Agent 编排器 — 支持 ReAct + 工具链推理。

    Usage:
        orch = MultiAgentOrchestrator(pipeline)
        result = orch.run("减震器阻尼比如何计算？")
    """

    def __init__(self, pipeline=None, max_iterations: int = 3, tools_registry: dict | None = None):
        self.pipeline = pipeline
        self.max_iterations = max_iterations
        self.tools = tools_registry or {}
        self.conversation: list[AgentMessage] = []

    def run(self, question: str, history: list = None, enable_react: bool = True) -> dict:
        """执行完整的多 Agent 协作流程"""
        self.conversation = []
        t0 = time.perf_counter()

        # ── Phase 1: Planner 分层规划 ──
        plan = self._planner_think(question)
        logger.info(f"Planner 生成计划: complexity={plan.get('complexity')}, sub_questions={plan.get('sub_questions', [])}")

        # ── Phase 2: Retriever 并行检索 ──
        evidence = self._retriever_execute_parallel(plan)
        logger.info(f"Retriever 收集证据: {len(evidence.get('chunks', []))} chunks, {len(evidence.get('sources', []))} sources")

        # ── Phase 3: ReAct Agent 工具链推理 ──
        react_result = None
        if enable_react and self.tools and self._should_use_tools(question, plan):
            react_result = self._react_execute(question, evidence, history)
            logger.info(f"ReAct 工具链完成: {react_result.get('tool_calls', 0)} tool calls")
            if react_result.get("answer"):
                evidence["chunks"].append(f"[ReAct Result]\n{react_result['answer']}")

        # ── Phase 4: 生成初始答案 ──
        answer = self._generate_initial(question, evidence, history)
        citations = answer.get("citations", {})

        # ── Phase 5: Critic 反思循环 ──
        for iteration in range(self.max_iterations):
            critique = self._critic_review(question, answer.get("answer", ""), evidence)
            logger.info(f"Critic 第{iteration+1}轮: score={critique.get('score', 0):.2f}")

            if critique.get("score", 0) >= 0.8:
                break

            if critique.get("missing_info"):
                supplementary = self._retriever_execute_parallel({"sub_questions": critique["missing_info"]})
                evidence["chunks"].extend(supplementary.get("chunks", []))
                evidence["sources"].extend(supplementary.get("sources", []))
                answer = self._generate_initial(question, evidence, history)
                citations = answer.get("citations", {})

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "question": question,
            "answer": answer.get("answer", ""),
            "citations": citations,
            "plan": plan,
            "react_used": react_result is not None,
            "tool_calls": react_result.get("tool_calls", 0) if react_result else 0,
            "iterations": iteration + 1,
            "critique_score": critique.get("score", 0),
            "evidence_count": len(evidence.get("chunks", [])),
            "latency_ms": elapsed,
        }

    # ── Planner (增强版 — 分层任务分解) ──

    def _planner_think(self, question: str) -> dict:
        prompt = f"""你是一个高级检索规划专家。对问题进行分析并制定分层检索计划。

输出 JSON 格式：
{{
    "complexity": "simple|medium|complex",
    "goal": "用户真正想要解决的问题",
    "sub_questions": ["子问题1", "子问题2", ...],
    "search_keywords": ["关键词1", "关键词2", ...],
    "domain": "领域名",
    "needs_tools": true/false,
    "needs_calculation": true/false,
    "needs_external_info": true/false,
    "expected_answer_type": "factual|procedural|comparative|explanatory"
}}

问题：{question}

计划 JSON:"""
        try:
            resp = self.pipeline.generator._llm.generate(prompt, options={"temperature": 0, "num_predict": 300})
            start = resp.find("{")
            end = resp.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(resp[start:end])
        except Exception:
            pass
        return {
            "complexity": "medium",
            "goal": question,
            "sub_questions": [question],
            "search_keywords": question.split(),
            "domain": "general",
            "needs_tools": False,
            "needs_calculation": False,
            "needs_external_info": False,
            "expected_answer_type": "factual",
        }

    # ── Retriever (并行增强版) ──

    def _retriever_execute_parallel(self, plan: dict) -> dict:
        all_chunks = []
        all_sources = []
        sub_questions = plan.get("sub_questions", [plan.get("search_keywords", [""])[0]])

        def _search_query(sq: str):
            chunks = []
            sources = []
            try:
                texts, indices = self.pipeline.retriever.hybrid_search(str(sq), top_k=5)
                chunks.extend(texts)
                for idx in indices:
                    if hasattr(self.pipeline.retriever, "chunk_metadata") and 0 <= idx < len(self.pipeline.retriever.chunk_metadata):
                        meta = self.pipeline.retriever.chunk_metadata[idx]
                        if meta:
                            sources.append(meta.get("source", ""))
            except Exception as e:
                logger.warning(f"Retriever sub-query failed for '{sq}': {e}")
            return chunks, sources

        with ThreadPoolExecutor(max_workers=min(len(sub_questions[:5]), 3)) as executor:
            futures = [executor.submit(_search_query, sq) for sq in sub_questions[:5]]
            for future in as_completed(futures):
                chunks, sources = future.result()
                all_chunks.extend(chunks)
                all_sources.extend(sources)

        seen = set()
        unique_chunks = []
        for c in all_chunks:
            if c not in seen:
                seen.add(c)
                unique_chunks.append(c)

        return {"chunks": unique_chunks[:20], "sources": list(set(all_sources))[:15]}

    # ── ReAct Agent ──

    def _should_use_tools(self, question: str, plan: dict) -> bool:
        if plan.get("needs_tools") or plan.get("needs_calculation") or plan.get("needs_external_info"):
            return True
        tool_keywords = ["计算", "算一下", "多少", "等于", "搜索", "查一下", "最新", "今天", "天气", "时间", "日期", "翻译", "换算"]
        q_lower = question.lower()
        return any(kw in q_lower for kw in tool_keywords)

    def _react_execute(self, question: str, evidence: dict, history: list | None) -> dict:
        try:
            from core.agent_loop import ReActAgent

            context_chunks = evidence.get("chunks", [])[:10]
            agent = ReActAgent(
                generator=self.pipeline.generator,
                tools_registry=self.tools,
                retriever=self.pipeline.retriever if hasattr(self.pipeline, "retriever") else None,
                max_iterations=3,
            )
            return agent.run(question, history=history, context_chunks=context_chunks)
        except ImportError:
            return {"answer": "", "tool_calls": 0}
        except Exception as e:
            logger.warning(f"ReAct execution failed: {e}")
            return {"answer": "", "tool_calls": 0}

    # ── Generator ──

    def _generate_initial(self, question: str, evidence: dict, history: list | None = None) -> dict:
        try:
            return self.pipeline.query(question, history=history)
        except Exception:
            try:
                return self.pipeline.generator.generate(question, evidence.get("chunks", [])[:10], history=history)
            except Exception:
                return {"answer": "Unable to generate answer.", "citations": {}}

    # ── Critic (增强版) ──

    def _critic_review(self, question: str, answer: str, evidence: dict) -> dict:
        ctx_summary = "\n".join(evidence.get("chunks", [])[:3])[:500]

        prompt = f"""你是一个严格的答案审查员。评估以下答案是否基于证据、准确回答了问题。

输出 JSON 格式：
{{"score": 0.0-1.0, "hallucination": true/false, "completeness": 0.0-1.0, "relevance": 0.0-1.0, "missing_info": ["缺失的信息点"], "suggestion": "改进建议"}}

问题：{question}
证据摘要：{ctx_summary}
答案：{answer[:1000]}

评估 JSON:"""
        try:
            resp = self.pipeline.generator._llm.generate(prompt, options={"temperature": 0, "num_predict": 300})
            start = resp.find("{")
            end = resp.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(resp[start:end])
        except Exception:
            pass
        return {"score": 0.7, "hallucination": False, "completeness": 0.7, "relevance": 0.7, "missing_info": [], "suggestion": ""}


# ── 便捷函数 ──


def run_multi_agent(question: str, pipeline=None, max_iterations: int = 3, enable_react: bool = True) -> dict:
    """一键运行多 Agent 协作（支持 ReAct 工具链）"""
    tools = {}
    try:
        from core.tools import _registry

        tools = _registry
    except ImportError:
        pass
    orch = MultiAgentOrchestrator(pipeline=pipeline, max_iterations=max_iterations, tools_registry=tools)
    return orch.run(question, enable_react=enable_react)
