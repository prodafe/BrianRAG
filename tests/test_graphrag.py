"""GraphRAG 社区摘要测试"""



class TestCommunityDetection:
    def test_detect_on_small_graph(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False, "ENABLE_GRAPH": True, "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "", "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b", "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()
        gb.graph.add_edge("A", "B", relation="连接")
        gb.graph.add_edge("B", "C", relation="连接")
        gb.graph.add_edge("D", "E", relation="关联")

        communities = gb.detect_communities()
        assert len(communities) >= 1
        for c in communities:
            assert len(c) >= 1

    def test_detect_empty_graph(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False, "ENABLE_GRAPH": True, "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "", "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b", "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()
        communities = gb.detect_communities()
        assert communities == []

    def test_summarize_communities(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False, "ENABLE_GRAPH": True, "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "", "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b", "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()
        gb.graph.add_edge("机器人", "调度系统", relation="属于")
        gb.graph.add_edge("调度系统", "任务分配", relation="执行")
        gb.graph.add_edge("机器人", "传感器", relation="搭载")

        class MockLLM:
            def generate(self, prompt, **kw):
                return "这个社区描述了机器人调度系统的核心架构。"

        result = gb.summarize_communities(max_communities=1, llm=MockLLM())
        if result:
            assert "entities" in result[0]
            assert "summary" in result[0]

    def test_stats_includes_communities(self, monkeypatch):
        mock_cfg = type("C", (), {
            "ENABLE_ENTITY_NORMALIZATION": False, "ENABLE_GRAPH": True, "GRAPH_FILE": "",
            "SPLINK_BLOCKING_RULE": "", "SPLINK_COMPARISON_LEVELS": [1, 2],
            "SPLINK_JARO_WINKLER_THRESHOLDS": [0.9, 0.95],
            "TRIPLE_EXTRACT_MODEL": "qwen2.5:7b", "LLM_MODEL": "qwen2.5:7b",
        })()
        monkeypatch.setattr("core.graph_builder.Config", mock_cfg)
        from core.graph_builder import GraphBuilder

        gb = GraphBuilder()
        gb.graph.add_edge("A", "B", relation="连接")
        gb.graph.add_edge("B", "C", relation="连接")

        stats = gb.get_stats()
        assert "communities" in stats
        assert "largest_community" in stats
