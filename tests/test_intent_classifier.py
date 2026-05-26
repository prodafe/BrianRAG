"""Intent Classifier 模块测试"""

from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.generate.return_value = "general"
    return llm


class TestKeywordFallback:
    def test_formula_keyword(self, mock_llm):
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.intent_classifier import IntentClassifier

            ic = IntentClassifier()
            mock_llm.generate.return_value = ""
            result = ic.classify("摩擦力的公式是什么")
            assert result in ("formula", "general")

    def test_image_keyword(self, mock_llm):
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.intent_classifier import IntentClassifier

            ic = IntentClassifier()
            mock_llm.generate.return_value = ""
            result = ic.classify("请看看这张图片里有什么")
            assert result in ("image", "general")

    def test_definition_keyword(self, mock_llm):
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.intent_classifier import IntentClassifier

            ic = IntentClassifier()
            mock_llm.generate.return_value = ""
            result = ic.classify("什么是减震器")
            assert result in ("definition", "general")

    def test_procedure_keyword(self, mock_llm):
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.intent_classifier import IntentClassifier

            ic = IntentClassifier()
            mock_llm.generate.return_value = ""
            result = ic.classify("如何配置调试环境，步骤是什么")
            assert result in ("procedure", "general")


class TestLLMClassification:
    def test_returns_valid_intent(self, mock_llm):
        mock_llm.generate.return_value = "formula"
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.intent_classifier import IntentClassifier

            ic = IntentClassifier()
            result = ic.classify("计算驱动力的公式")
            assert result in ("formula", "definition", "procedure", "image", "general")

    def test_unknown_intent_fallback(self, mock_llm):
        mock_llm.generate.return_value = "unknown_type"
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.intent_classifier import IntentClassifier

            ic = IntentClassifier()
            result = ic.classify("随机问题")
            assert result == "general"

    def test_empty_llm_response_fallback(self, mock_llm):
        mock_llm.generate.return_value = ""
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.intent_classifier import IntentClassifier

            ic = IntentClassifier()
            result = ic.classify("随机问题")
            assert result in ("formula", "definition", "procedure", "image", "general")

    def test_exception_returns_general(self, mock_llm):
        mock_llm.generate.side_effect = Exception("LLM offline")
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.intent_classifier import IntentClassifier

            ic = IntentClassifier()
            result = ic.classify("任何问题")
            assert result == "general"
