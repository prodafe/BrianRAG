"""工作流引擎测试"""

import pytest
from core.workflow_engine import (
    NodeType, WorkflowNode, WorkflowEdge, Workflow, WorkflowEngine, BUILTIN_TEMPLATES,
)


class TestWorkflowModels:
    def test_node_creation(self):
        n = WorkflowNode(id="1", type=NodeType.RETRIEVE, label="Search", config={"top_k": 5})
        assert n.id == "1"
        assert n.type == NodeType.RETRIEVE
        assert n.config["top_k"] == 5

    def test_workflow_serialization(self):
        nodes = [WorkflowNode(id="1", type=NodeType.INPUT, label="Q")]
        edges = [WorkflowEdge(source="1", target="2")]
        wf = Workflow(id="test", name="Test", nodes=nodes, edges=edges)
        d = wf.to_dict()
        assert d["id"] == "test"
        assert len(d["nodes"]) == 1
        assert len(d["edges"]) == 1

    def test_workflow_deserialization(self):
        d = {
            "id": "wf1", "name": "Test",
            "nodes": [{"id": "n1", "type": "input", "label": "Q", "config": {}, "position": {"x": 0, "y": 0}}],
            "edges": [{"source": "n1", "target": "n2"}],
        }
        wf = Workflow.from_dict(d)
        assert wf.id == "wf1"
        assert len(wf.nodes) == 1


class TestWorkflowEngine:
    def test_simple_workflow(self, monkeypatch):
        monkeypatch.setattr("core.retriever.HybridRetriever._init_success", False, raising=False)
        engine = WorkflowEngine()
        nodes = [
            WorkflowNode(id="in", type=NodeType.INPUT, label="Q"),
            WorkflowNode(id="out", type=NodeType.OUTPUT, label="Result"),
        ]
        wf = Workflow(id="test", name="Simple", nodes=nodes, edges=[WorkflowEdge("in", "out")])
        result = engine.run(wf, {"question": "test"})
        assert result["workflow_id"] == "test"

    def test_topological_sort(self):
        engine = WorkflowEngine()
        node_map = {"a": WorkflowNode("a", NodeType.INPUT, ""), "b": WorkflowNode("b", NodeType.OUTPUT, ""),
                     "c": WorkflowNode("c", NodeType.RETRIEVE, "")}
        adj = {"a": ["b", "c"], "b": [], "c": ["b"]}
        order = engine._topological_sort(node_map, adj)
        assert order[0] == "a"
        assert order[-1] == "b"

    def test_register_tool(self):
        engine = WorkflowEngine()
        engine.register_tool("echo", lambda x: f"echo: {x}")
        assert "echo" in engine.tools


class TestBuiltinTemplates:
    def test_basic_rag_template(self):
        assert "basic_rag" in BUILTIN_TEMPLATES
        t = BUILTIN_TEMPLATES["basic_rag"]
        assert len(t["nodes"]) == 4
        assert len(t["edges"]) == 3

    def test_agent_template(self):
        assert "agent_with_tools" in BUILTIN_TEMPLATES
        t = BUILTIN_TEMPLATES["agent_with_tools"]
        assert any(n["type"] == "condition" for n in t["nodes"])
        assert any(n["type"] == "tool" for n in t["nodes"])
