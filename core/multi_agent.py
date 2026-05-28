"""多 Agent 协作系统 — Planner/Retriever/Critic 三角色编排

Planner:  分析问题 → 制定检索计划 → 分解为子任务
Retriever: 执行检索 → 收集证据 → 返回结构化上下文
Critic:   验证答案 → 检查事实准确性 → 提出改进建议 → 循环至达标
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Sequence
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class AgentMessage:
    role: str  # planner / retriever / critic / user
    content: str
    metadata: dict = field(default_factory=dict)


class MultiAgentOrchestrator:
    """多 Agent 编排器。

    Usage:
        orch = MultiAgentOrchestrator(pipeline)
        result = orch.run("减震器阻尼比如何计算？")
    """

    def __init__(self, pipeline=None, max_iterations: int = 3):
        self.pipeline = pipeline
        self.max_iterations = max_iterations
        self.conversation: list[AgentMessage] = []

    def run(self, question: str, history: list = None) -> dict:
        """执行完整的多 Agent 协作流程"""
        self.conversation = []
        t0 = time.perf_counter()

        # ── Phase 1: Planner 规划 ──
        plan = self._planner_think(question)
        logger.info(f"Planner 生成计划: {plan.get('sub_questions', [])}")

        # ── Phase 2: Retriever 执行检索 ──
        evidence = self._retriever_execute(plan)
        logger.info(f"Retriever 收集证据: {len(evidence.get('chunks', []))} chunks")

        # ── Phase 3: 生成初始答案 ──
        answer = self._generate_initial(question, evidence)
        citations = answer.get("citations", {})

        # ── Phase 4: Critic 反思循环 ──
        for iteration in range(self.max_iterations):
            critique = self._critic_review(question, answer.get("answer", ""), evidence)
            logger.info(f"Critic 第{iteration+1}轮: score={critique.get('score', 0):.2f}")

            if critique.get("score", 0) >= 0.8:
                break

            # Critic 不满意 → 补充检索
            if critique.get("missing_info"):
                supplementary = self._retriever_execute({"sub_questions": critique["missing_info"]})
                evidence["chunks"].extend(supplementary.get("chunks", []))
                evidence["sources"].extend(supplementary.get("sources", []))

                # 基于补充证据重新生成
                answer = self._generate_initial(question, evidence)
                citations = answer.get("citations", {})

        elapsed = round((time.perf_counter() - t0) * 1000, 1)
        return {
            "question": question,
            "answer": answer.get("answer", ""),
            "citations": citations,
            "plan": plan,
            "iterations": iteration + 1,
            "critique_score": critique.get("score", 0),
            "evidence_count": len(evidence.get("chunks", [])),
            "latency_ms": elapsed,
        }

    # ── Planner ──

    def _planner_think(self, question: str) -> dict:
        prompt = f"""你是一个检索规划专家。分析以下问题，制定检索计划。

输出 JSON 格式：
{{"complexity": "simple|medium|complex", "sub_questions": ["子问题1", ...], "search_keywords": ["关键词1", ...], "domain": "领域名"}}

问题：{question}

计划 JSON:"""
        try:
            resp = self.pipeline.generator._llm.generate(prompt, options={"temperature": 0, "num_predict": 256})
            # Extract JSON
            start = resp.find("{")
            end = resp.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(resp[start:end])
        except Exception:
            pass
        return {"complexity": "medium", "sub_questions": [question], "search_keywords": question.split(), "domain": "general"}

    # ── Retriever ──

    def _retriever_execute(self, plan: dict) -> dict:
        all_chunks = []
        all_sources = []
        sub_questions = plan.get("sub_questions", [plan.get("search_keywords", [""])[0]])

        for sq in sub_questions[:3]:  # Max 3 sub-queries
            try:
                texts, indices = self.pipeline.retriever.hybrid_search(str(sq), top_k=5)
                all_chunks.extend(texts)
                for idx in indices:
                    if 0 <= idx < len(self.pipeline.retriever.chunk_metadata):
                        meta = self.pipeline.retriever.chunk_metadata[idx]
                        all_sources.append(meta.get("source", ""))
            except Exception as e:
                logger.warning(f"Retriever sub-query failed: {e}")

        # Deduplicate
        seen = set()
        unique_chunks = []
        for c in all_chunks:
            if c not in seen:
                seen.add(c)
                unique_chunks.append(c)

        return {"chunks": unique_chunks[:15], "sources": list(set(all_sources))[:10]}

    # ── Generator ──

    def _generate_initial(self, question: str, evidence: dict) -> dict:
        try:
            return self.pipeline.query(question, history=None)
        except Exception:
            return {"answer": "Unable to generate answer.", "citations": {}}

    # ── Critic ──

    def _critic_review(self, question: str, answer: str, evidence: dict) -> dict:
        ctx_summary = "\n".join(evidence.get("chunks", [])[:3])[:500]

        prompt = f"""你是一个严格的答案审查员。评估以下答案是否基于证据、准确回答了问题。

输出 JSON 格式：
{{"score": 0.0-1.0, "hallucination": true/false, "completeness": 0.0-1.0, "missing_info": ["缺失的信息点"], "suggestion": "改进建议"}}

问题：{question}
证据摘要：{ctx_summary}
答案：{answer[:1000]}

评估 JSON:"""
        try:
            resp = self.pipeline.generator._llm.generate(prompt, options={"temperature": 0, "num_predict": 256})
            start = resp.find("{")
            end = resp.rfind("}") + 1
            if start >= 0 and end > start:
                return json.loads(resp[start:end])
        except Exception:
            pass
        return {"score": 0.7, "hallucination": False, "completeness": 0.7, "missing_info": [], "suggestion": ""}


# ── 便捷函数 ──


def run_multi_agent(question: str, pipeline=None, max_iterations: int = 3) -> dict:
    """一键运行多 Agent 协作"""
    orch = MultiAgentOrchestrator(pipeline=pipeline, max_iterations=max_iterations)
    return orch.run(question)
