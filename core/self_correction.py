import re
import logging
from typing import Any

from config import Config

logger = logging.getLogger(__name__)


class SelfCorrector:
    def __init__(self) -> None:
        self.model: str = Config.LLM_MODEL

    @property
    def _llm(self) -> Any:
        from core.llm_provider import get_llm_provider

        return get_llm_provider()

    def correct(self, question: str, answer: str, contexts: list[str], threshold: float = 0.6) -> tuple[str, dict]:
        """自我修正：评估答案质量，低分别基于上下文重新生成"""
        score = self.evaluate_answer(question, answer, contexts)
        if score >= threshold:
            return answer, {}

        # 分数太低，基于上下文重新生成
        context_text = "\n".join([c[:500] for c in contexts[:5]])
        prompt = f"""你是一个严谨的知识库助手。请基于以下参考信息，直接、准确地回答问题。不要编造任何参考信息中没有的内容。

参考信息：
{context_text}

问题：{question}

回答（只基于参考信息，如有公式请用 LaTeX）："""
        try:
            resp = self._llm.chat(
                messages=[{"role": "user", "content": prompt}], options={"temperature": 0.1, "top_p": 0.9}
            )
            corrected = resp
            # 提取引用
            import re

            citations = {}
            matches = re.findall(r"\[(\d+)\]", corrected)
            for num in set(matches):
                idx = int(num) - 1
                if 0 <= idx < len(contexts):
                    citations[num] = contexts[idx]
            return corrected, citations
        except Exception as e:
            return answer, {}

    def evaluate_answer(self, question: str, answer: str, context_chunks: list[str]) -> float:
        # 防御：如果没有上下文，最高得分为0
        if not context_chunks:
            return 0.0

        # 只取前3个片段的前200字符作为摘要
        summary = "\n".join([c[:200] for c in context_chunks[:3]])
        prompt = f"""你是一个答案质量评估器。请判断以下答案是否基于提供的上下文片段，并且直接回答了问题。
返回一个0到1之间的数字，只输出数字，不要有其他内容。
0=完全无关或胡编乱造，0.5=部分相关但不够完整或依赖外部知识，1=完全基于上下文且准确回答问题。

问题：{question}
答案：{answer}
上下文（摘要）：{summary}

得分："""
        try:
            response = self._llm.chat(messages=[{"role": "user", "content": prompt}])
            score_text = response["message"]["content"].strip()
            match = re.search(r"(\d+(?:\.\d+)?)", score_text)
            if match:
                score = float(match.group(1))
                return min(max(score, 0.0), 1.0)
            else:
                return 0.5
        except Exception as e:
            logger.warning(f"评估失败: {e}")
            return 0.5

    def rewrite_query(self, original_query: str) -> str:
        prompt = f"""请将以下用户问题改写成更适合信息检索的表述，可以增加同义词或更具体的关键词，但不要改变原意。
只输出改写后的问题，不要包含任何额外解释。输出长度不要超过200个字符。

原始问题：{original_query}
改写后的问题："""
        try:
            response = self._llm.chat(messages=[{"role": "user", "content": prompt}])
            new_query = response["message"]["content"].strip()
            if new_query and len(new_query) <= 500:  # 安全限制
                return new_query
        except Exception as e:
            logger.warning(f"查询改写失败: {e}")
        return original_query
