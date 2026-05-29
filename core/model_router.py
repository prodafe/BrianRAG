"""模型智能路由 — 根据查询复杂度自动选择最优模型"""

import logging

from config import Config

logger = logging.getLogger(__name__)

_COMPLEX_KEYWORDS = ["解释", "分析", "比较", "为什么", "怎么实现", "如何设计", "优缺点", "区别",
                     "详细", "深入", "总结", "概括", "评估"]


class ModelRouter:
    """根据查询意图和复杂度自动选择模型。

    Usage:
        router = ModelRouter()
        model, provider = router.route(intent="formula", question="...")
        llm = get_llm_provider()
        answer = llm.generate(prompt, model=model)
    """

    def __init__(self):
        self._route_stats = {"simple": 0, "normal": 0, "complex": 0}

    def route(self, intent: str, question: str) -> tuple[str, str | None]:
        """返回 (model_name, provider_name)。provider 为 None 时使用默认 provider。"""
        if not getattr(Config, "enable_model_routing", True):
            return Config.llm_model, None

        q_len = len(question)
        is_complex = self._is_complex(intent, question)

        if is_complex:
            self._route_stats["complex"] += 1
            model = getattr(Config, "complex_model", None)
            if model:
                logger.info(f"路由: complex → {model} (q_len={q_len}, intent={intent})")
                return model, None
            return Config.llm_model, None

        if q_len < 20 and intent == "general":
            self._route_stats["simple"] += 1
            model = getattr(Config, "simple_model", None)
            if model:
                logger.debug(f"路由: simple → {model}")
                return model, None
            return Config.evaluator_model, None

        self._route_stats["normal"] += 1
        return Config.llm_model, None

    def _is_complex(self, intent: str, question: str) -> bool:
        """判断问题是否复杂，需要更强模型。"""
        if intent in ("formula", "procedure"):
            return True
        if len(question) > 100:
            return True
        q_lower = question.lower()
        threshold = getattr(Config, "complex_threshold_keywords", None)
        keywords = threshold if threshold else _COMPLEX_KEYWORDS
        return any(kw in q_lower for kw in keywords)

    @property
    def stats(self) -> dict:
        return dict(self._route_stats)
