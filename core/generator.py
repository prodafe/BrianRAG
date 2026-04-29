import hashlib
import pickle
import os
from typing import Any

import ollama
from ollama import Client
from config import Config

class Generator:
    def __init__(self):
        self.cache = {}
        self._load_cache()
        # 创建客户端，指定 Ollama 服务地址
        self.client = Client(host=Config.OLLAMA_BASE_URL)

    def _load_cache(self):
        cache_file = os.path.join(Config.CACHE_DIR, "answers.pkl")
        if os.path.exists(cache_file):
            with open(cache_file, "rb") as f:
                self.cache = pickle.load(f)

    def _save_cache(self):
        with open(os.path.join(Config.CACHE_DIR, "answers.pkl"), "wb") as f:
            pickle.dump(self.cache, f)

    def _hash(self, query, context):
        text = query + "".join(context)
        return hashlib.md5(text.encode()).hexdigest()

    def generate(self, query: str, context_chunks: list[str], history: list = None):
        if not context_chunks:
            return "未找到相关信息。", {}

        key = self._hash(query, context_chunks)
        if Config.ENABLE_CACHE and key in self.cache:
            return self.cache[key], {}  # 缓存命中时没有引用信息（可以简单返回空）

        # 构建带编号的上下文（用于提示模型）
        numbered_context = ""
        for i, chunk in enumerate(context_chunks, 1):
            numbered_context += f"[{i}] {chunk}\n\n"

        # 构建历史对话字符串
        history_text = ""
        if history:
            history_text = "以下是之前的对话记录：\n"
            for msg in history[-Config.MAX_HISTORY_TURNS * 2:]:
                role = "用户" if msg["role"] == "user" else "助手"
                history_text += f"{role}: {msg['content']}\n"
            history_text += "\n"

        # 修改后的 prompt，要求模型输出引用编号
        prompt = f"""{history_text}基于以下信息回答问题。如果信息不足，请明确说“根据现有资料无法回答”。
   **重要**：请在回答中，对于每个引用的事实，在句子末尾加上对应的编号，格式为 [数字]。例如，如果你引用了第一条信息，请写“...（[1]）”。
    信息（带编号）：
    {numbered_context}
    问题：{query}
    答案："""

        client = ollama.Client(host=Config.OLLAMA_BASE_URL)
        try:
            response = client.chat(model=Config.LLM_MODEL, messages=[{"role": "user", "content": prompt}],options={"temperature": 0.1, "top_p": 0.9})
            answer = response["message"]["content"]
        except Exception as e:
            answer = f"生成答案时出错：{e}"
            return answer, {}

        # 提取引用标记
        citations = self._extract_citations(answer, context_chunks)

        if Config.ENABLE_CACHE:
            # 缓存时只存答案，不存引用（引用可根据答案和上下文重新提取）
            self.cache[key] = answer
            self._save_cache()

        return answer, citations

    def _extract_citations(self, answer: str, context_chunks: list[str]) -> dict:
        import re
        citations = {}
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, answer)
        for num in set(matches):
            idx = int(num) - 1
            if 0 <= idx < len(context_chunks):
                citations[num] = context_chunks[idx]
        return citations