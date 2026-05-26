import logging
from typing import Any

from config import Config

logger = logging.getLogger(__name__)


class IntentClassifier:
    def __init__(self, model: str | None = None) -> None:
        self.model: str = model or getattr(Config, "EVALUATOR_MODEL", "qwen2.5:1.5b")
        self.intents: list[str] = ["formula", "definition", "procedure", "image", "general"]

    @property
    def _llm(self) -> Any:
        from core.llm_provider import get_small_llm

        return get_small_llm()

    def classify(self, query: str) -> str:
        prompt = f"""判断以下用户问题的意图类别，只输出一个词：formula / definition / procedure / image / general。

含义：
- formula: 询问公式、计算方式、表达式、方程式等
- definition: 询问定义、是什么、概念、含义
- procedure: 询问步骤、方法、流程、操作步骤
- image: 询问图片、图像、示意图、结构图、照片等
- general: 其他一般性问题

问题：{query}
意图："""
        try:
            intent = self._llm.generate(prompt, options={"temperature": 0, "num_predict": 16}).strip().lower()
            if intent in self.intents:
                return intent
            logger.warning(f"未知意图: {intent}，回退为 general")
            return "general"
        except Exception as e:
            logger.error(f"意图识别失败: {e}，回退为 general")
            return "general"
