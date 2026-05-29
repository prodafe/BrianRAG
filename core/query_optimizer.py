# core/query_optimizer.py
import json
import logging
import random
from typing import Any

from config import Config

logger = logging.getLogger(__name__)


class QueryOptimizer:
    def __init__(self) -> None:
        self.model: str = Config.LLM_MODEL

    @property
    def _llm(self) -> Any:
        from core.llm_provider import get_llm_provider

        return get_llm_provider()

    def optimize_batch(self, question: str) -> dict[str, Any]:
        """一次 LLM 调用完成查询改写、HyDE、多查询生成、复合检测，减少 LLM 调用次数"""
        prompt = f"""分析以下用户问题，输出 JSON（不要 markdown 代码块，只输出 JSON）：

{{
  "rewritten": "更适合检索的改写版本（增加关键词但不变原意）",
  "hyde": "一段假设性文档内容，直接回答该问题（100-200字）",
  "variants": ["不同表述1", "不同表述2", "不同表述3"],
  "is_compound": true/false,
  "sub_questions": ["子问题1", "子问题2"]
}}

规则：
- rewritten: 如果原问题已经足够清晰，原样返回
- hyde: 模拟知识库文档的语气，包含专业术语
- variants: 2-3个不同表述，用于多路召回
- is_compound: 仅当问题明显包含 2+ 个独立子问题时为 true
- sub_questions: 如果 is_compound=true，列出子问题；否则为空数组

问题：{question}
JSON："""
        try:
            resp = self._llm.generate(prompt, options={"temperature": 0.1, "num_predict": 512})
            # 清理可能的 markdown 代码块
            resp = resp.strip()
            if resp.startswith("```"):
                resp = resp.split("\n", 1)[-1]
                if resp.endswith("```"):
                    resp = resp[:-3]
            result = json.loads(resp)
            logger.info(
                f"批量优化完成: rewrite={len(result.get('rewritten', ''))}chars, "
                f"hyde={len(result.get('hyde', ''))}chars, variants={len(result.get('variants', []))}"
            )
            return result
        except Exception as e:
            logger.warning(f"批量优化失败: {e}，回退到原问题")
            return {
                "rewritten": question,
                "hyde": question,
                "variants": [question],
                "is_compound": False,
                "sub_questions": [],
            }

    # ── 向后兼容的单方法（委托给 _llm）──
    def rewrite_query(self, original_query: str) -> str:
        prompt = f"""请将以下用户问题改写成更适合信息检索的表述，可以增加同义词或更具体的关键词，但不要改变原意。
只输出改写后的问题，不要包含任何额外解释。

原始问题：{original_query}
改写后的问题："""
        try:
            result = self._llm.generate(prompt, options={"temperature": 0, "num_predict": 128})
            return result if result else original_query
        except Exception:
            return original_query

    def hyde_document(self, query: str) -> str:
        prompt = f"""请根据以下问题，生成一篇假设性的文档，该文档应该直接回答问题，并且包含可能出现在真实文档中的关键信息。
只输出文档内容，不要包含"假设文档"等额外说明。

问题：{query}
假设文档："""
        try:
            result = self._llm.generate(prompt, options={"temperature": 0.1, "num_predict": 256})
            return result if result else query
        except Exception:
            return query

    def expand_with_synonyms(self, query: str) -> str:
        try:
            import os

            syn_path = os.path.join(Config.DATA_DIR, "synonyms.json")
            with open(syn_path, encoding="utf-8") as f:
                syn_dict = json.load(f)
        except FileNotFoundError:
            return query
        words = query.split()
        new_words = [random.choice(syn_dict[w]) for w in words if w in syn_dict]
        return query + " " + " ".join(new_words) if new_words else query

    def decompose_query(self, question: str) -> list[str]:
        split_markers = [
            "？以及",
            "？还有",
            "？另外",
            "？同时",
            "？分别",
            "？并",
            "？且",
            "？和",
            "？与",
            "。另外",
            "。同时",
            "。此外",
            "。并且",
        ]
        has_split = any(m in question for m in split_markers)
        has_list_marker = any(kw in question for kw in ["分别", "各自", "依次"])
        if not has_split and not has_list_marker:
            return [question]

        prompt = f"""判断以下问题是否为复合问题（包含多个独立子问题）。如果是，请将其拆解为独立的子问题，每行一个。如果不是复合问题，直接原样输出原问题。

问题：{question}
子问题列表（每行一个，或原问题）："""
        try:
            resp = self._llm.generate(prompt, options={"temperature": 0, "num_predict": 256})
            lines = [l.strip() for l in resp.split("\n") if l.strip()]
            if len(lines) <= 1:
                return [question]
            sub_queries = [l for l in lines if len(l) > 3 and ("？" in l or "什么" in l or "如何" in l or "怎么" in l)]
            if len(sub_queries) >= 2:
                logger.info(f"问题拆解成功: {question[:50]}... → {len(sub_queries)} 个子问题")
                return sub_queries
        except Exception as e:
            logger.warning(f"问题拆解失败: {e}")
        return [question]

    def generate_multi_queries(self, question: str, num_queries: int = 3) -> list[str]:
        try:
            prompt = f"""请将以下问题用{num_queries}种不同的方式重新表述，保持原意。每行一个，不要编号。
问题：{question}
不同表述："""
            resp = self._llm.generate(prompt, options={"temperature": 0.1, "num_predict": 80})
            lines = [line.strip() for line in resp.split("\n") if line.strip()]
            queries = [line for line in lines if not line.startswith("不同表述") and not line.startswith("问题")]
            queries = list(dict.fromkeys(queries))[:num_queries]
            return [question] + queries if queries else [question]
        except Exception:
            return [question]

    def answer_with_decomposition(self, question: str, pipeline) -> dict:
        """查询分解 + 逐个子问题检索 + 合并答案。

        对于复杂问题，分解后分别检索，最后 LLM 综合所有子答案。
        """
        sub_queries = self.decompose_query(question)
        if len(sub_queries) <= 1:
            return pipeline.query(question)

        # 并行检索子问题
        sub_results = []
        for sq in sub_queries:
            try:
                r = pipeline.query(sq, history=None)
                sub_results.append({"question": sq, "answer": r.get("answer", ""), "chunks": r.get("used_chunks", [])})
            except Exception:
                sub_results.append({"question": sq, "answer": "", "chunks": []})

        # 合并所有子答案
        sub_answers = "\n\n".join(
            f"Q: {r['question']}\nA: {r['answer']}" for r in sub_results if r["answer"]
        )
        all_chunks = []
        for r in sub_results:
            all_chunks.extend(r.get("chunks", []))

        merge_prompt = f"""基于以下子问题的回答，综合给出一个完整、连贯的回答。不要重复子问题的结构，而是自然整合信息。

原始问题：{question}

子问题及回答：
{sub_answers}

综合回答："""
        try:
            merged = self._llm.generate(merge_prompt, options={"temperature": 0.1})
            return {
                "question": question,
                "answer": merged.strip(),
                "used_chunks": all_chunks,
                "sub_queries": sub_queries,
                "sub_results": [{"question": r["question"], "answer": r["answer"][:200]} for r in sub_results],
            }
        except Exception:
            # Fallback: return concatenated sub-answers
            return {
                "question": question,
                "answer": sub_answers,
                "used_chunks": all_chunks,
                "sub_queries": sub_queries,
            }
