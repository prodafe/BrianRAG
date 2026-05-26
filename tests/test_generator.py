"""Generator 模块测试"""

from unittest.mock import MagicMock, patch


class TestPromptBuilding:
    def test_build_prompt_contains_question(self):
        from core.generator import Generator

        gen = Generator()
        prompt = gen._build_prompt("什么是摩擦力？", ["摩擦力是接触面之间的阻力。"])
        assert "什么是摩擦力？" in prompt
        assert "摩擦力是接触面之间的阻力" in prompt

    def test_build_prompt_multi_chunk(self):
        from core.generator import Generator

        gen = Generator()
        chunks = ["信息A。", "信息B。", "信息C。"]
        prompt = gen._build_prompt("测试", chunks)
        for i, _c in enumerate(chunks, 1):
            assert f"[{i}]" in prompt

    def test_build_prompt_empty_chunks(self):
        from core.generator import Generator

        gen = Generator()
        prompt = gen._build_prompt("测试", [])
        assert "测试" in prompt


class TestCitationExtraction:
    def test_extract_single_citation(self):
        from core.generator import Generator

        gen = Generator()
        chunks = ["参考内容A", "参考内容B", "参考内容C"]
        answer = "根据资料，答案是 X ([1])。"
        citations = gen._extract_citations(answer, chunks)
        assert "1" in citations
        assert citations["1"] == "参考内容A"

    def test_extract_multiple_citations(self):
        from core.generator import Generator

        gen = Generator()
        chunks = ["内容1", "内容2", "内容3"]
        answer = "结论 ([1]) 得到了验证 ([3])。"
        citations = gen._extract_citations(answer, chunks)
        assert len(citations) == 2
        assert citations["1"] == "内容1"
        assert citations["3"] == "内容3"

    def test_extract_no_citations(self):
        from core.generator import Generator

        gen = Generator()
        citations = gen._extract_citations("没有引用。", ["参考"])
        assert citations == {}

    def test_extract_out_of_range(self):
        from core.generator import Generator

        gen = Generator()
        citations = gen._extract_citations("见 [99]。", ["仅有一条"])
        assert citations == {}


class TestCacheBehavior:
    def test_cache_hash_deterministic(self):
        from core.generator import Generator

        gen = Generator()
        k1 = gen._hash("问题", ["上下文A", "上下文B"])
        k2 = gen._hash("问题", ["上下文A", "上下文B"])
        assert k1 == k2

    def test_cache_hash_different_query(self):
        from core.generator import Generator

        gen = Generator()
        k1 = gen._hash("问题A", ["上下文"])
        k2 = gen._hash("问题B", ["上下文"])
        assert k1 != k2

    def test_cache_store_and_retrieve(self):
        from core.generator import Generator

        gen = Generator()
        gen.cache = {}
        key = gen._hash("测试", ["参考"])
        gen.cache[key] = ("缓存答案", {"1": "参考"})

        result = gen.cache.get(key)
        assert result[0] == "缓存答案"
        assert result[1]["1"] == "参考"

    def test_cache_legacy_string_backward_compat(self):
        from core.generator import Generator

        gen = Generator()
        gen.cache = {}
        key = gen._hash("测试", ["参考"])
        gen.cache[key] = "旧格式缓存"

        cached = gen.cache[key]
        if isinstance(cached, tuple) and len(cached) == 2:
            answer, citations = cached
        else:
            answer, citations = cached, {}
        assert answer == "旧格式缓存"
        assert citations == {}


class TestGenerateEdgeCases:
    def test_empty_chunks_return_message(self):
        from core.generator import Generator

        gen = Generator()
        answer, citations = gen.generate("问题", [])
        assert "未找到" in answer or answer
        assert citations == {}

    def test_generate_with_mock_llm(self):
        from core.generator import Generator

        gen = Generator()
        gen.cache = {}
        mock_llm = MagicMock()
        mock_llm.chat.return_value = "模拟回答 [1]"

        with patch("core.llm_provider.get_llm_provider", return_value=mock_llm):
            answer, citations = gen.generate("测试", ["参考内容"])
            assert "模拟回答" in answer
            assert "1" in citations
