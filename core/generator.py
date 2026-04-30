import hashlib
import pickle
import os
import re
import ollama
from ollama import Client
from config import Config

class Generator:
    def __init__(self):
        self.cache = {}
        self._load_cache()
        self.client = Client(host=Config.OLLAMA_BASE_URL)
        self.model = Config.LLM_MODEL   # 添加模型属性供流式生成使用

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

    def _build_prompt(self, question: str, context_chunks: list[str], history: list = None) -> str:
        """构建强化版提示词，支持复杂内容（公式、表格、代码等）"""
        # 1. 编号上下文
        numbered_context = ""
        for i, chunk in enumerate(context_chunks, 1):
            # 标记特殊内容类型，便于模型识别
            chunk_type = ""
            if "```" in chunk:
                chunk_type = " [代码块]"
            elif "|" in chunk and chunk.count("|") > 2:
                chunk_type = " [表格]"
            elif any(sym in chunk for sym in ["=", "+", "-", "*", "/", "∑", "∫", "Δ", "μ"]):
                chunk_type = " [公式]"
            numbered_context += f"[{i}]{chunk_type} {chunk}\n\n"

        # 2. 历史对话
        history_text = ""
        if history:
            history_text = "## 对话历史\n"
            for msg in history[-Config.MAX_HISTORY_TURNS * 2:]:
                role = "用户" if msg["role"] == "user" else "助手"
                history_text += f"- {role}: {msg['content']}\n"
            history_text += "\n"

        # 3. 核心指令
        prompt = f"""你是一个专业的知识库助手。请基于【参考信息】准确、完整地回答用户的问题。

    {history_text}
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
    5. **图片处理**: - 如果参考信息中包含图片链接（格式为 `![描述](路径)`），你可以直接在回答中使用它，例如：`![描述](路径)`。 - 不要对图片链接进行额外的解释或修改，直接原样输出即可。 - 将图片放在相关段落的下方，不要连续放置过多图片。

    ## 问题
    {question}

    ## 回答
    """
        return prompt

    def generate(self, query: str, context_chunks: list[str], history: list = None):
        if not context_chunks:
            return "未找到相关信息。", {}

        key = self._hash(query, context_chunks)
        if Config.ENABLE_CACHE and key in self.cache:
            return self.cache[key], {}

        prompt = self._build_prompt(query, context_chunks, history)

        try:
            response = self.client.chat(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.1, "top_p": 0.9}
            )
            answer = response["message"]["content"]
        except Exception as e:
            answer = f"生成答案时出错：{e}"
            return answer, {}

        citations = self._extract_citations(answer, context_chunks)

        if Config.ENABLE_CACHE:
            self.cache[key] = answer
            self._save_cache()

        return answer, citations

    def _extract_citations(self, answer: str, context_chunks: list[str]) -> dict:
        citations = {}
        pattern = r'\[(\d+)\]'
        matches = re.findall(pattern, answer)
        for num in set(matches):
            idx = int(num) - 1
            if 0 <= idx < len(context_chunks):
                citations[num] = context_chunks[idx]
        return citations

    def generate_stream(self, question: str, chunks: list[str], history: list = None):
        """流式生成答案"""
        if not chunks:
            yield "未找到相关信息。"
            return

        prompt = self._build_prompt(question, chunks, history)

        try:
            # 使用 generate 方法并开启流式输出
            stream = self.client.generate(
                model=self.model,
                prompt=prompt,
                options={"temperature": 0.1, "top_p": 0.9},
                stream=True
            )
            for chunk in stream:
                # 每个 chunk 包含 'response' 字段
                yield chunk['response']
        except Exception as e:
            yield f"生成答案时出错：{e}"