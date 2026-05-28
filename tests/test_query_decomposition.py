"""查询分解测试"""



class MockLLM:
    def generate(self, prompt, **kw):
        if "分解" in prompt:
            return "什么是弹簧预压力\n弹簧预压力的计算公式\n弹簧预压力在减震器中的应用"
        return "综合回答内容。"


class TestQueryDecomposition:
    def test_decompose_simple_returns_original(self, monkeypatch):
        monkeypatch.setattr("core.llm_provider.get_llm_provider", lambda: MockLLM())
        from core.query_optimizer import QueryOptimizer

        qo = QueryOptimizer()
        result = qo.decompose_query("减震器结构设计要点")
        assert len(result) >= 1
        assert isinstance(result[0], str)

    def test_decompose_complex(self, monkeypatch):
        monkeypatch.setattr("core.llm_provider.get_llm_provider", lambda: MockLLM())
        from core.query_optimizer import QueryOptimizer

        qo = QueryOptimizer()
        result = qo.decompose_query("弹簧预压力的作用和计算方法以及在减震器中的应用")
        assert len(result) >= 1

    def test_decompose_empty_result(self, monkeypatch):
        class EmptyLLM:
            def generate(self, prompt, **kw):
                return ""

        monkeypatch.setattr("core.llm_provider.get_llm_provider", lambda: EmptyLLM())
        from core.query_optimizer import QueryOptimizer

        qo = QueryOptimizer()
        result = qo.decompose_query("test")
        assert len(result) >= 1
        assert result[0] == "test"  # fallback to original
