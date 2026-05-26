import hashlib
import json
import os
import pickle
import re
from collections.abc import Iterator
from typing import Any

from config import Config


class Generator:
    def __init__(self) -> None:
        self.cache: dict[str, tuple[str, dict]] = {}
        self._load_cache()
        self.model: str = Config.LLM_MODEL
        self.few_shot_examples: dict[str, str] = self._load_few_shot_examples()

    @property
    def _llm(self) -> Any:
        from core.llm_provider import get_llm_provider

        return get_llm_provider()

    def _load_few_shot_examples(self) -> dict[str, str]:
        """加载 Few-shot 示例库"""
        examples_file = os.path.join(Config.DATA_DIR, "few_shot_examples.json")
        if os.path.exists(examples_file):
            with open(examples_file, encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _load_cache(self) -> None:
        cache_file = os.path.join(Config.CACHE_DIR, "answers.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                self.cache = pickle.load(f)

    def _save_cache(self) -> None:
        os.makedirs(Config.CACHE_DIR, exist_ok=True)
        with open(os.path.join(Config.CACHE_DIR, "answers.pkl"), "wb") as f:
            pickle.dump(self.cache, f)

    def _hash(self, query: str, context: list[str]) -> str:
        text = query + "".join(context)
        return hashlib.md5(text.encode()).hexdigest()

    def _build_few_shot(self, intent: str) -> str:
        """根据意图构建 Few-shot 示例"""
        examples = self.few_shot_examples.get(intent, [])
        if not examples:
            return ""
        few_shot_text = "## 示例\n"
        for ex in examples[:2]:  # 最多两个示例
            few_shot_text += f"问题：{ex['question']}\n回答：{ex['answer']}\n\n"
        return few_shot_text

    _feedback_seeded = False

    @classmethod
    def _seed_feedback(cls):
        """首次调用时将 feedback.jsonl 中的 negative 条目加载到 Redis"""
        if cls._feedback_seeded:
            return
        cls._feedback_seeded = True
        try:
            import json as _json

            import redis as _rds

            rc = _rds.Redis(host="localhost", port=6379, db=0, decode_responses=True)
            if rc.exists("feedback:negative"):
                return
            fb_file = os.path.join(Config.BASE_DIR, "feedback.jsonl")
            if os.path.exists(fb_file):
                with open(fb_file, encoding="utf-8") as f:
                    for line in f:
                        entry = _json.loads(line.strip())
                        if entry.get("feedback") == "negative":
                            rc.hset("feedback:negative", entry["question"], entry.get("comment", "需要更详细的回答"))
        except Exception:
            pass

    def _check_feedback(self, question: str) -> str:
        """检查类似问题是否收到过 negative 反馈，返回增强指令"""
        self._seed_feedback()
        try:
            from difflib import SequenceMatcher

            import redis as _rds

            rc = _rds.Redis(host="localhost", port=6379, db=0, decode_responses=True)
            all_neg = rc.hgetall("feedback:negative")
            for neg_q, comment in all_neg.items():
                if SequenceMatcher(None, question, neg_q).ratio() > 0.6:
                    return f"\n⚠️ **重要提醒**：类似问题此前回答被用户反馈「{comment}」。请务必基于参考信息给出**更完整、更详细**的回答，确保覆盖所有关键点。\n"
        except Exception:
            pass
        return ""

    def _build_prompt(
        self, question: str, context_chunks: list[str], history: list | None = None, intent: str = "general"
    ) -> str:
        """构建强化版提示词，支持 Few-shot 和意图感知"""
        # 编号上下文
        numbered_context = ""
        for i, chunk in enumerate(context_chunks, 1):
            chunk_type = ""
            if "```" in chunk:
                chunk_type = " [代码块]"
            elif "|" in chunk and chunk.count("|") > 2:
                chunk_type = " [表格]"
            elif any(sym in chunk for sym in ["=", "+", "-", "*", "/", "∑", "∫", "Δ", "μ"]):
                chunk_type = " [公式]"
            numbered_context += f"[{i}]{chunk_type} {chunk}\n\n"

        # 历史对话
        history_text = ""
        if history:
            history_text = "## 对话历史\n"
            for msg in history[-Config.MAX_HISTORY_TURNS * 2 :]:
                role = "用户" if msg["role"] == "user" else "助手"
                history_text += f"- {role}: {msg['content']}\n"
            history_text += "\n"

        # Few-shot 示例
        few_shot_text = self._build_few_shot(intent)

        # 反馈增强指令
        feedback_note = self._check_feedback(question)

        # 工具调用
        from core.tools import get_tools_prompt

        tools_text = get_tools_prompt()

        prompt = f"""你是一个专业的知识库助手。请基于【参考信息】准确、完整地回答用户的问题。
{feedback_note}

{history_text}
{few_shot_text}
{tools_text}

## 参考信息
{numbered_context}

## 回答要求
1. **引用标注**：在引用某条信息时，在句子末尾加上对应的编号，格式为 `[数字]`。例如：“驱动轮公式为 F = μ·N ([2])”。
2. **复杂内容处理**：
   - **公式**：使用标准 LaTeX 行内格式 `\\( ... \\)` 或行间格式 `\\[ ... \\]`。变量名不需要用 `\\text{{}}` 包裹，直接使用希腊字母或斜体（如 `\\Delta`, `\\sigma`, `F_{{N1}}`）。
   - **表格**：若参考信息中包含表格，优先用自然语言描述关键数据；必要时可转换为 Markdown 表格呈现。
   - **代码**：若参考信息中有代码，请用代码块（```语言）包裹，并保持缩进。
   - **步骤/流程**：使用编号列表（1. 2. 3. ...）清晰说明。
   - **定义**：用加粗或引用块突出关键术语。
3. **信息不足**：如果参考信息不足以回答问题，请明确说“根据现有资料无法回答”，不要编造信息。
4. **语言风格**：简洁、专业、直接。避免冗余修饰，不要输出无关内容（如“根据参考信息”等开场白）。
5. **图片处理**：如果参考信息中包含图片链接（格式为 `![描述](路径)`），你可以直接在回答中使用它，例如：`![描述](路径)`。不要对图片链接进行额外的解释或修改，直接原样输出即可。将图片放在相关段落的下方，不要连续放置过多图片。

## 问题
{question}

## 回答
"""
        return prompt

    def generate(
        self, query: str, context_chunks: list[str], history: list | None = None, intent: str = "general"
    ) -> tuple[str, dict]:
        if not context_chunks:
            return "未找到相关信息。", {}

        key = self._hash(query, context_chunks)
        if Config.ENABLE_CACHE and key in self.cache:
            cached = self.cache[key]
            if isinstance(cached, tuple) and len(cached) == 2:
                return cached  # (answer, citations)
            return cached, {}  # legacy plain string

        prompt = self._build_prompt(query, context_chunks, history, intent)

        try:
            answer = self._llm.chat([{"role": "user", "content": prompt}], options={"temperature": 0.1, "top_p": 0.9})
        except Exception as e:
            answer = f"生成答案时出错：{e}"
            return answer, {}

        # 检测并执行工具调用
        if "[TOOL:" in answer:
            from core.tools import execute_tool_call

            tool_result = execute_tool_call(answer)
            if tool_result and not tool_result.startswith("未知工具") and not tool_result.startswith("工具调用失败"):
                enriched = [f"[工具返回] {tool_result}"] + context_chunks
                try:
                    answer = self._llm.chat(
                        [{"role": "user", "content": self._build_prompt(query, enriched, history, intent)}],
                        options={"temperature": 0.1, "top_p": 0.9},
                    )
                except Exception:
                    answer = f"{answer}\n\n[工具结果] {tool_result}"

        citations = self._extract_citations(answer, context_chunks)

        if Config.ENABLE_CACHE:
            self.cache[key] = (answer, citations)
            self._save_cache()

        return answer, citations

    def _extract_citations(self, answer: str, context_chunks: list[str]) -> dict[str, str]:
        citations = {}
        pattern = r"\[(\d+)\]"
        matches = re.findall(pattern, answer)
        for num in set(matches):
            idx = int(num) - 1
            if 0 <= idx < len(context_chunks):
                citations[num] = context_chunks[idx]
        return citations

    def generate_stream(
        self, question: str, chunks: list[str], history: list | None = None, intent: str = "general"
    ) -> Iterator[str]:
        """流式生成答案"""
        if not chunks:
            yield "未找到相关信息。"
            return

        prompt = self._build_prompt(question, chunks, history, intent)

        try:
            yield from self._llm.chat_stream(
                [{"role": "user", "content": prompt}], options={"temperature": 0.1, "top_p": 0.9}
            )
        except Exception as e:
            yield f"生成答案时出错：{e}"
