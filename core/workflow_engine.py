"""Agent 可视化工作流引擎

支持 JSON 定义工作流，4 种节点类型，并行分支执行。
节点类型: retrieve | generate | tool | condition
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class NodeType(str, Enum):
    RETRIEVE = "retrieve"
    GENERATE = "generate"
    TOOL = "tool"
    CONDITION = "condition"
    INPUT = "input"
    OUTPUT = "output"


@dataclass
class WorkflowNode:
    id: str
    type: NodeType
    label: str = ""
    config: dict = field(default_factory=dict)
    position: dict = field(default_factory=dict)  # {x, y} for frontend


@dataclass
class WorkflowEdge:
    source: str
    target: str
    label: str = ""
    condition: str = ""  # for condition branches: "true" / "false"


@dataclass
class Workflow:
    id: str
    name: str
    description: str = ""
    nodes: list[WorkflowNode] = field(default_factory=list)
    edges: list[WorkflowEdge] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "nodes": [{"id": n.id, "type": n.type.value, "label": n.label, "config": n.config, "position": n.position} for n in self.nodes],
            "edges": [{"source": e.source, "target": e.target, "label": e.label, "condition": e.condition} for e in self.edges],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Workflow":
        nodes = [WorkflowNode(id=n["id"], type=NodeType(n["type"]), label=n.get("label", ""),
                              config=n.get("config", {}), position=n.get("position", {})) for n in d.get("nodes", [])]
        edges = [WorkflowEdge(source=e["source"], target=e["target"], label=e.get("label", ""),
                              condition=e.get("condition", "")) for e in d.get("edges", [])]
        return cls(id=d["id"], name=d["name"], description=d.get("description", ""), nodes=nodes, edges=edges)


# ── 工作流执行引擎 ──


class WorkflowEngine:
    """执行工作流图。

    Usage:
        engine = WorkflowEngine(pipeline, tools_registry)
        result = engine.run(workflow, initial_input={"question": "..."})
    """

    def __init__(self, pipeline=None):
        self.pipeline = pipeline
        self.tools: dict[str, Callable] = {}

    def register_tool(self, name: str, func: Callable):
        self.tools[name] = func

    def run(self, workflow: Workflow, initial_input: dict) -> dict:
        """执行工作流。按拓扑顺序执行节点，支持条件分支和并行。"""
        state: dict[str, Any] = {"input": initial_input, "node_outputs": {}, "history": []}
        node_map = {n.id: n for n in workflow.nodes}
        adj = self._build_adjacency(workflow)

        # Topological sort
        order = self._topological_sort(node_map, adj)

        for node_id in order:
            node = node_map[node_id]
            try:
                output = self._execute_node(node, state)
                state["node_outputs"][node_id] = output
                state["history"].append({"node": node_id, "type": node.type.value, "output": str(output)[:200], "time": time.time()})
            except Exception as e:
                logger.error(f"Workflow node {node_id} failed: {e}")
                state["node_outputs"][node_id] = {"error": str(e)}
                state["history"].append({"node": node_id, "type": node.type.value, "error": str(e), "time": time.time()})

        # Collect final output
        output_nodes = [n for n in workflow.nodes if n.type == NodeType.OUTPUT]
        if output_nodes:
            final = state["node_outputs"].get(output_nodes[0].id, {})
        else:
            final = state

        return {"result": final, "state": state, "workflow_id": workflow.id}

    def _execute_node(self, node: WorkflowNode, state: dict) -> Any:
        q = state["input"].get("question", "")

        if node.type == NodeType.INPUT:
            return state["input"]

        elif node.type == NodeType.RETRIEVE:
            top_k = node.config.get("top_k", 5)
            if self.pipeline and self.pipeline.retriever:
                texts, indices = self.pipeline.retriever.hybrid_search(q, top_k=top_k)
                return {"texts": texts, "indices": indices, "count": len(texts)}
            return {"texts": [], "indices": []}

        elif node.type == NodeType.GENERATE:
            context = state["node_outputs"]
            # Find upstream retrieve node output
            retrieve_output = None
            for nid, out in context.items():
                if isinstance(out, dict) and "texts" in out:
                    retrieve_output = out
                    break
            chunks = retrieve_output.get("texts", []) if retrieve_output else []
            model = node.config.get("model", "default")
            if self.pipeline:
                answer, citations = self.pipeline.generator.generate(q, chunks, model=model if model != "default" else None)
                return {"answer": answer, "citations": citations}
            return {"answer": "Pipeline not available"}

        elif node.type == NodeType.TOOL:
            tool_name = node.config.get("tool", "")
            tool_arg = node.config.get("arg", q)
            func = self.tools.get(tool_name)
            if func:
                result = func(tool_arg)
                return {"tool_result": str(result)}
            return {"tool_result": f"Tool '{tool_name}' not found"}

        elif node.type == NodeType.CONDITION:
            condition = node.config.get("expression", "")
            # Simple condition evaluation: check if keyword exists in question
            keyword = node.config.get("keyword", "")
            if keyword and keyword.lower() in q.lower():
                return {"branch": "true"}
            return {"branch": "false"}

        elif node.type == NodeType.OUTPUT:
            return state.get("node_outputs", {})

        return {}

    def _build_adjacency(self, workflow: Workflow) -> dict[str, list[str]]:
        adj: dict[str, list[str]] = {}
        for node in workflow.nodes:
            adj[node.id] = []
        for edge in workflow.edges:
            if edge.source in adj:
                adj[edge.source].append(edge.target)
        return adj

    def _topological_sort(self, node_map: dict, adj: dict) -> list[str]:
        in_degree = {nid: 0 for nid in node_map}
        for src, targets in adj.items():
            for tgt in targets:
                if tgt in in_degree:
                    in_degree[tgt] += 1

        queue = [nid for nid, d in in_degree.items() if d == 0]
        result = []
        while queue:
            nid = queue.pop(0)
            result.append(nid)
            for tgt in adj.get(nid, []):
                in_degree[tgt] -= 1
                if in_degree[tgt] == 0:
                    queue.append(tgt)
        return result


# ── 内置工作流模板 ──

BUILTIN_TEMPLATES = {
    "basic_rag": {
        "id": "basic_rag", "name": "Basic RAG", "description": "检索→生成 标准流程",
        "nodes": [
            {"id": "in", "type": "input", "label": "Question", "config": {}, "position": {"x": 100, "y": 200}},
            {"id": "ret", "type": "retrieve", "label": "Retrieve", "config": {"top_k": 5}, "position": {"x": 300, "y": 200}},
            {"id": "gen", "type": "generate", "label": "Generate", "config": {"model": "default"}, "position": {"x": 500, "y": 200}},
            {"id": "out", "type": "output", "label": "Answer", "config": {}, "position": {"x": 700, "y": 200}},
        ],
        "edges": [
            {"source": "in", "target": "ret"}, {"source": "ret", "target": "gen"}, {"source": "gen", "target": "out"},
        ],
    },
    "agent_with_tools": {
        "id": "agent_with_tools", "name": "Agent + Tools", "description": "检索→条件判断→工具调用→生成",
        "nodes": [
            {"id": "in", "type": "input", "label": "Question", "config": {}, "position": {"x": 100, "y": 200}},
            {"id": "ret", "type": "retrieve", "label": "Retrieve", "config": {"top_k": 5}, "position": {"x": 300, "y": 150}},
            {"id": "cond", "type": "condition", "label": "Need Calc?", "config": {"keyword": "计算"}, "position": {"x": 500, "y": 150}},
            {"id": "calc", "type": "tool", "label": "Calculator", "config": {"tool": "calc"}, "position": {"x": 700, "y": 80}},
            {"id": "gen1", "type": "generate", "label": "Generate", "config": {}, "position": {"x": 700, "y": 220}},
            {"id": "gen2", "type": "generate", "label": "Generate+Tool", "config": {}, "position": {"x": 500, "y": 300}},
            {"id": "out", "type": "output", "label": "Answer", "config": {}, "position": {"x": 900, "y": 200}},
        ],
        "edges": [
            {"source": "in", "target": "ret"}, {"source": "ret", "target": "cond"},
            {"source": "cond", "target": "calc", "condition": "true"}, {"source": "cond", "target": "gen1", "condition": "false"},
            {"source": "calc", "target": "gen2"}, {"source": "gen1", "target": "out"}, {"source": "gen2", "target": "out"},
        ],
    },
}
