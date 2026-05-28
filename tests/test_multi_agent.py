"""多 Agent 协作测试"""



class TestMultiAgentOrchestrator:
    def test_initialization(self):
        from core.multi_agent import MultiAgentOrchestrator

        orch = MultiAgentOrchestrator(max_iterations=2)
        assert orch.max_iterations == 2
        assert orch.conversation == []

    def test_planner_think(self, monkeypatch):
        monkeypatch.setattr("core.llm_provider.get_llm_provider", lambda: _MockLLM())

        class MockPipeline:
            generator = type("_", (), {"_llm": _MockLLM()})()

        from core.multi_agent import MultiAgentOrchestrator

        orch = MultiAgentOrchestrator(pipeline=MockPipeline())
        plan = orch._planner_think("减震器阻尼比如何计算？")
        assert "complexity" in plan
        assert "sub_questions" in plan

    def test_critic_review(self, monkeypatch):
        monkeypatch.setattr("core.llm_provider.get_llm_provider", lambda: _MockLLM())

        class MockPipeline:
            generator = type("_", (), {"_llm": _MockLLM()})()

        from core.multi_agent import MultiAgentOrchestrator

        orch = MultiAgentOrchestrator(pipeline=MockPipeline())
        critique = orch._critic_review("test q", "test answer", {"chunks": ["evidence"]})
        assert 0 <= critique.get("score", 0) <= 1

    def test_agent_message(self):
        from core.multi_agent import AgentMessage

        msg = AgentMessage(role="planner", content="Plan: ...", metadata={"complexity": "medium"})
        assert msg.role == "planner"
        assert msg.metadata["complexity"] == "medium"


class _MockLLM:
    def generate(self, prompt, **kw):
        import json
        if "检索规划" in prompt:
            return json.dumps({"complexity": "medium", "sub_questions": ["q1"], "search_keywords": ["test"], "domain": "engineering"})
        if "审查员" in prompt:
            return json.dumps({"score": 0.85, "hallucination": False, "completeness": 0.9, "missing_info": [], "suggestion": ""})
        return "Mock response"
