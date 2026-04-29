# core/query_optimizer.py
import ollama
from config import Config

class QueryOptimizer:
    def __init__(self):
        self.client = ollama.Client(host=Config.OLLAMA_BASE_URL)
        self.model = Config.LLM_MODEL   # 使用主模型或单独配置

    def rewrite_query(self, original_query: str) -> str:
        """改写查询，使其更适合信息检索"""
        prompt = f"""请将以下用户问题改写成更适合信息检索的表述，可以增加同义词或更具体的关键词，但不要改变原意。
只输出改写后的问题，不要包含任何额外解释。

原始问题：{original_query}
改写后的问题："""
        try:
            response = self.client.generate(model=self.model, prompt=prompt)
            new_query = response["response"].strip()
            if new_query:
                return new_query
        except Exception as e:
            print(f"查询改写失败: {e}")
        return original_query

    def hyde_document(self, query: str) -> str:
        """生成假设性文档（HyDE），用于向量检索"""
        prompt = f"""请根据以下问题，生成一篇假设性的文档，该文档应该直接回答问题，并且包含可能出现在真实文档中的关键信息。
只输出文档内容，不要包含“假设文档”等额外说明。

问题：{query}
假设文档："""
        try:
            response = self.client.generate(model=self.model, prompt=prompt)
            hyde = response["response"].strip()
            if hyde:
                return hyde
        except Exception as e:
            print(f"HyDE 生成失败: {e}")
        return query   # 失败时回退到原查询