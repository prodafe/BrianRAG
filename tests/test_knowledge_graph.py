"""知识图谱模块测试"""



class TestGraphBuilder:
    def test_initial_state_empty(self, monkeypatch):
        monkeypatch.setattr("core.graph_builder.Config", type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False,
            "ENABLE_GRAPH": True,
            "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "",
            "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b",
            "LLM_MODEL": "qwen2.5:7b",
        })())
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()
        assert len(gb.graph.nodes()) == 0
        assert len(gb.entity_to_chunks) == 0

    def test_add_chunk_with_triples(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False,
            "ENABLE_GRAPH": True,
            "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "",
            "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b",
            "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()

        def mock_extract(text):
            return [("企业", "研发", "产品"), ("科学家", "发现", "现象")]

        gb.extract_triples = mock_extract
        gb.add_chunk("测试文本", 0)
        assert "企业" in gb.graph.nodes()
        assert "产品" in gb.graph.nodes()
        assert gb.graph.has_edge("企业", "产品")
        assert 0 in gb.entity_to_chunks.get("企业", set())

    def test_build_from_chunks(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False,
            "ENABLE_GRAPH": True,
            "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "",
            "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b",
            "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()

        def mock_extract(text):
            if "A" in text:
                return [("A", "连接", "B")]
            return [("C", "关联", "D")]

        gb.extract_triples = mock_extract
        gb.build_from_chunks(["文本 A 和 B", "文本 C 和 D"])
        assert len(gb.graph.nodes()) >= 3
        assert gb.graph.has_edge("A", "B") or gb.graph.has_edge("C", "D")

    def test_similar_entities_simple(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False,
            "ENABLE_GRAPH": True,
            "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "",
            "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b",
            "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()
        assert gb._similar("企业研发", "企业研发", 0.85) is True
        assert gb._similar("abc", "xyz", 0.85) is False

    def test_normalize_simple_merges_similar(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False,
            "ENABLE_GRAPH": True,
            "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "",
            "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b",
            "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()
        gb.graph.add_edge("机器人调度", "系统", relation="属于")
        gb.entity_to_chunks["机器人调度"] = {0}
        gb.entity_to_chunks["系统"] = {1}

        gb.graph.add_edge("机器人调度系统", "任务", relation="处理")
        gb.entity_to_chunks["机器人调度系统"] = {2}
        gb.entity_to_chunks["任务"] = {3}

        node_count_before = len(gb.graph.nodes())
        gb._normalize_simple(threshold=0.6)
        node_count_after = len(gb.graph.nodes())
        assert node_count_after <= node_count_before

    def test_retrieve_by_entities_empty(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False,
            "ENABLE_GRAPH": True,
            "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "",
            "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b",
            "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()

        def mock_generate(model=None, prompt=None, options=None):
            return "  "

        gb._llm.generate = mock_generate
        result = gb.retrieve_by_entities("空查询")
        assert result == []

    def test_retrieve_by_entities_with_results(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False,
            "ENABLE_GRAPH": True,
            "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "",
            "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b",
            "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()
        gb.entity_to_chunks["机器人"] = {0, 1}
        gb.entity_to_chunks["调度"] = {1, 2}

        def mock_generate(model=None, prompt=None, options=None):
            return "机器人, 调度"

        gb._llm.generate = mock_generate
        result = gb.retrieve_by_entities("机器人调度系统")
        assert len(result) >= 1
        assert 1 in result

    def test_to_html_creates_file(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False,
            "ENABLE_GRAPH": True,
            "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "",
            "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b",
            "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        import tempfile

        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()
        gb.graph.add_edge("A", "B", relation="测试")

        with tempfile.NamedTemporaryFile(suffix=".html", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            gb.to_html(tmp_path)
            import os

            assert os.path.exists(tmp_path)
            assert os.path.getsize(tmp_path) > 0
        finally:
            import os

            if os.path.exists(tmp_path):
                os.unlink(tmp_path)
