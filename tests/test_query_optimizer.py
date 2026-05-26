"""Query Optimizer 模块测试"""
import pytest
from unittest.mock import MagicMock, patch


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    llm.generate.return_value = "改写后的查询"
    return llm


class TestRewriteQuery:
    def test_rewrite_returns_string(self, mock_llm):
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.query_optimizer import QueryOptimizer
            opt = QueryOptimizer()
            result = opt.rewrite_query("原始查询问题")
            assert isinstance(result, str)
            assert len(result) > 0

    def test_rewrite_llm_failure_returns_original(self, mock_llm):
        mock_llm.generate.side_effect = Exception("LLM down")
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.query_optimizer import QueryOptimizer
            opt = QueryOptimizer()
            result = opt.rewrite_query("原始查询")
            assert result == "原始查询"

    def test_rewrite_empty_llm_response(self, mock_llm):
        mock_llm.generate.return_value = ""
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.query_optimizer import QueryOptimizer
            opt = QueryOptimizer()
            result = opt.rewrite_query("原始查询")
            assert result == "原始查询"


class TestHydeDocument:
    def test_hyde_returns_string(self, mock_llm):
        mock_llm.generate.return_value = "假设文档内容"
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.query_optimizer import QueryOptimizer
            opt = QueryOptimizer()
            result = opt.hyde_document("什么是RAG")
            assert isinstance(result, str)

    def test_hyde_failure_fallback(self, mock_llm):
        mock_llm.generate.side_effect = Exception("down")
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.query_optimizer import QueryOptimizer
            opt = QueryOptimizer()
            result = opt.hyde_document("查询")
            assert isinstance(result, str)


class TestMultiQuery:
    def test_multi_query_returns_list(self, mock_llm):
        mock_llm.generate.return_value = "查询1\n查询2\n查询3"
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.query_optimizer import QueryOptimizer
            opt = QueryOptimizer()
            queries = opt.generate_multi_queries("测试问题")
            assert isinstance(queries, list)
            assert len(queries) > 0

    def test_multi_query_failure_returns_original(self, mock_llm):
        mock_llm.generate.side_effect = Exception("down")
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.query_optimizer import QueryOptimizer
            opt = QueryOptimizer()
            queries = opt.generate_multi_queries("问题")
            assert queries == ["问题"]


class TestOptimizeBatch:
    def test_batch_returns_dict(self, mock_llm):
        mock_llm.generate.return_value = "改写后的查询"
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.query_optimizer import QueryOptimizer
            opt = QueryOptimizer()
            result = opt.optimize_batch("测试")
            assert isinstance(result, dict)
            assert "rewritten" in result
            assert "hyde" in result
            assert "variants" in result


class TestDecomposeQuery:
    def test_decompose_failure_returns_original(self, mock_llm):
        mock_llm.generate.side_effect = Exception("down")
        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            from core.query_optimizer import QueryOptimizer
            opt = QueryOptimizer()
            result = opt.decompose_query("复杂问题")
            assert result == ["复杂问题"]
