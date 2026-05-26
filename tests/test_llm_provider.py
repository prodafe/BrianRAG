"""LLM Provider + SelfCorrector 模块测试"""
import pytest
from unittest.mock import MagicMock, patch


class TestProviderFactory:
    def test_get_llm_provider_ollama(self):
        from config import Config

        Config.llm_provider = "ollama"
        from core.llm_provider import get_llm_provider, reset_providers

        reset_providers()
        with patch("core.llm_provider.OllamaLLMProvider") as mock:
            mock.return_value = MagicMock()
            provider = get_llm_provider()
            assert provider is not None

    def test_reset_providers(self):
        from config import Config

        Config.llm_provider = "ollama"
        from core.llm_provider import get_llm_provider, reset_providers

        reset_providers()
        with patch("core.llm_provider.OllamaLLMProvider") as mock:
            mock.return_value = MagicMock()
            p1 = get_llm_provider()
            reset_providers()
            mock.return_value = MagicMock()
            p2 = get_llm_provider()
            assert p1 is not p2


class TestBaseLLMProvider:
    def test_abstract_methods(self):
        from core.llm_provider import BaseLLMProvider

        with pytest.raises(TypeError):
            BaseLLMProvider()


class TestSelfCorrector:
    def test_evaluate_no_context_returns_zero(self):
        from core.self_correction import SelfCorrector

        sc = SelfCorrector()
        score = sc.evaluate_answer("问题", "答案", [])
        assert score == 0.0

    def test_correct_high_score_no_change(self):
        from core.self_correction import SelfCorrector

        sc = SelfCorrector()
        sc.evaluate_answer = MagicMock(return_value=0.9)
        answer, citations = sc.correct("问题", "原答案", ["上下文"])
        assert answer == "原答案"
        assert citations == {}

    def test_correct_low_score_retries(self):
        from core.self_correction import SelfCorrector

        sc = SelfCorrector()
        sc.evaluate_answer = MagicMock(return_value=0.3)
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "修正后的答案 [1]"

        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            answer, citations = sc.correct("问题", "低质量答案", ["上下文内容"])
            assert "修正后的答案" in answer
            assert "1" in citations

    def test_correct_llm_error_returns_original(self):
        from core.self_correction import SelfCorrector

        sc = SelfCorrector()
        sc.evaluate_answer = MagicMock(return_value=0.3)
        mock_llm = MagicMock()
        mock_llm.chat.side_effect = Exception("LLM error")

        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            answer, citations = sc.correct("问题", "原答案", ["上下文"])
            assert answer == "原答案"

    def test_correct_high_score_skips_retry(self):
        from core.self_correction import SelfCorrector

        sc = SelfCorrector()
        sc.evaluate_answer = MagicMock(return_value=0.85)
        answer, _ = sc.correct("问题", "好答案", ["上下文"], threshold=0.6)
        assert answer == "好答案"
