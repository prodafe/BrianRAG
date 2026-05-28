"""Tests for core/model_router.py"""

from core.model_router import ModelRouter


class TestModelRouter:
    def test_simple_question_uses_small_model(self):
        router = ModelRouter()
        model, _ = router.route("general", "你好")
        assert "1.5b" in model or "small" in model.lower() or model != "qwen2.5:7b"

    def test_formula_intent_uses_complex(self):
        router = ModelRouter()
        model, _ = router.route("formula", "F=ma")
        assert model != "qwen2.5:1.5b"

    def test_procedure_intent_uses_complex(self):
        router = ModelRouter()
        model, _ = router.route("procedure", "如何安装")
        assert model != "qwen2.5:1.5b"

    def test_long_question_uses_complex(self):
        router = ModelRouter()
        long_q = "请详细解释一下" + "这个" * 50
        model, _ = router.route("general", long_q)
        assert model != "qwen2.5:1.5b"

    def test_complex_keyword_triggers_routing(self):
        router = ModelRouter()
        model, _ = router.route("general", "请分析和比较这两种方案")
        assert model != "qwen2.5:1.5b"

    def test_route_returns_provider_none(self):
        router = ModelRouter()
        _, provider = router.route("general", "test")
        assert provider is None

    def test_stats_tracks_routing(self):
        router = ModelRouter()
        for _ in range(3):
            router.route("general", "你好")
        router.route("formula", "E=mc^2")
        stats = router.stats
        assert sum(stats.values()) == 4
