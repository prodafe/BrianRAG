import re
from config import Config
import ollama

class SelfCorrector:
    def __init__(self):
        self.client = ollama.Client(host=Config.OLLAMA_BASE_URL)
        self.model = Config.LLM_MODEL

    def evaluate_answer(self, question: str, answer: str, context_chunks: list) -> float:
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
            response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            score_text = response["message"]["content"].strip()
            match = re.search(r'(\d+(?:\.\d+)?)', score_text)
            if match:
                score = float(match.group(1))
                return min(max(score, 0.0), 1.0)
            else:
                return 0.5
        except Exception as e:
            print(f"评估失败: {e}")
            return 0.5

    def rewrite_query(self, original_query: str) -> str:
        prompt = f"""请将以下用户问题改写成更适合信息检索的表述，可以增加同义词或更具体的关键词，但不要改变原意。
只输出改写后的问题，不要包含任何额外解释。输出长度不要超过200个字符。

原始问题：{original_query}
改写后的问题："""
        try:
            response = self.client.chat(model=self.model, messages=[{"role": "user", "content": prompt}])
            new_query = response["message"]["content"].strip()
            if new_query and len(new_query) <= 500:   # 安全限制
                return new_query
        except Exception as e:
            print(f"查询改写失败: {e}")
        return original_query