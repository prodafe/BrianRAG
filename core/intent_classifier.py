import logging
import ollama
from config import Config

logger = logging.getLogger(__name__)

class IntentClassifier:
    def __init__(self, model: str = "qwen2.5:1.5b"):
        self.model = model
        self.client = ollama.Client(host=Config.OLLAMA_BASE_URL)
        self.intents = ["formula", "definition", "procedure", "general"]

    def classify(self, query: str) -> str:
        """
        返回意图类别: formula, definition, procedure, general
        """
        prompt = f"""判断以下用户问题的意图类别，只输出一个词：formula / definition / procedure / general。

含义：
- formula: 询问公式、计算方式、表达式、方程式等
- definition: 询问定义、是什么、概念、含义
- procedure: 询问步骤、方法、流程、操作步骤
- general: 其他一般性问题

问题：{query}
意图："""
        try:
            resp = self.client.generate(model=self.model, prompt=prompt, options={'temperature': 0, 'num_predict': 16})
            intent = resp["response"].strip().lower()
            if intent in self.intents:
                return intent
            else:
                logger.warning(f"未知意图: {intent}，回退为 general")
                return "general"
        except Exception as e:
            logger.error(f"意图识别失败: {e}，回退为 general")
            return "general"