import logging
import os
import pickle
from difflib import SequenceMatcher
from typing import Any

import networkx as nx
import pandas as pd

from config import Config

logger = logging.getLogger(__name__)


class GraphBuilder:
    def __init__(self) -> None:
        self.graph: nx.Graph = nx.Graph()
        self.entity_to_chunks: dict[str, set[int]] = {}

    @property
    def _llm(self) -> Any:
        from core.llm_provider import get_llm_provider

        return get_llm_provider()

    def extract_triples(self, text: str) -> list[tuple[str, str, str]]:
        prompt = f"""你是一个专业的信息抽取助手。请从以下文本中提取所有 (实体1, 关系, 实体2) 三元组。关系应当是一个简短的动词短语或名词性短语。每个三元组一行，格式为：实体1|关系|实体2。如果文本中没有明确的三元组，只输出“无”。

    文本：
    {text}

    输出示例：
    企业|研发|产品
    科学家|发现|现象

    现在开始输出："""
        try:
            resp = self._llm.generate(
                model=Config.TRIPLE_EXTRACT_MODEL, prompt=prompt, options={"temperature": 0, "num_predict": 512}
            )
            raw = resp.strip()
            logger.debug(f"模型输出: {raw}")
            lines = raw.split("\n")
            triples = []
            for line in lines:
                if "|" in line and not line.startswith("无"):
                    parts = line.split("|")
                    if len(parts) == 3:
                        triples.append(tuple(p.strip() for p in parts))
            return triples
        except Exception as e:
            logger.warning(f"三元组提取失败: {e}")
            return []

    def add_chunk(self, chunk_text: str, chunk_idx: int):
        triples = self.extract_triples(chunk_text)
        for subj, rel, obj in triples:
            self.graph.add_edge(subj, obj, relation=rel)
            for ent in [subj, obj]:
                if ent not in self.entity_to_chunks:
                    self.entity_to_chunks[ent] = set()
                self.entity_to_chunks[ent].add(chunk_idx)

    def build_from_chunks(self, chunks: list[str]):
        self.graph.clear()
        self.entity_to_chunks.clear()
        for idx, chunk in enumerate(chunks):
            self.add_chunk(chunk, idx)
        # 实体规范化（如果启用，带超时保护）
        if Config.ENABLE_ENTITY_NORMALIZATION and len(self.graph.nodes) > 1:
            try:
                from concurrent.futures import ThreadPoolExecutor, TimeoutError

                with ThreadPoolExecutor(max_workers=1) as executor:
                    future = executor.submit(self.normalize_entities)
                    future.result(timeout=getattr(Config, "graph_normalize_timeout", 300))
            except TimeoutError:
                logger.warning("实体规范化超时，跳过合并")
            except Exception as e:
                logger.warning(f"实体规范化异常，跳过: {e}")
        return self.graph

    def update_from_chunks(self, new_chunks: list[str], start_idx: int):
        for offset, chunk in enumerate(new_chunks):
            chunk_idx = start_idx + offset
            self.add_chunk(chunk, chunk_idx)
        # 增量更新后也可规范化（避免频繁可注释）
        if Config.ENABLE_ENTITY_NORMALIZATION and len(self.graph.nodes) > 1:
            self.normalize_entities()

    # ------ 实体规范化核心 ------
    def _similar(self, a: str, b: str, threshold: float = 0.85) -> bool:
        return SequenceMatcher(None, a, b).ratio() > threshold

    def _normalize_simple(self, threshold: float = 0.85):
        """简单的相似度合并（回退方案）"""
        nodes = list(self.graph.nodes())
        merged = set()
        for i, node1 in enumerate(nodes):
            if node1 in merged:
                continue
            for node2 in nodes[i + 1 :]:
                if node2 in merged:
                    continue
                if self._similar(node1, node2, threshold):
                    count1 = len(self.entity_to_chunks.get(node1, []))
                    count2 = len(self.entity_to_chunks.get(node2, []))
                    keep = node1 if count1 >= count2 else node2
                    remove = node2 if keep == node1 else node1
                    if keep not in self.entity_to_chunks:
                        self.entity_to_chunks[keep] = set()
                    self.entity_to_chunks[keep].update(self.entity_to_chunks.get(remove, set()))
                    for neighbor in list(self.graph.neighbors(remove)):
                        edge_data = self.graph.get_edge_data(remove, neighbor)
                        self.graph.add_edge(keep, neighbor, **(edge_data or {}))
                    self.graph.remove_node(remove)
                    if remove in self.entity_to_chunks:
                        del self.entity_to_chunks[remove]
                    merged.add(remove)

    def _normalize_by_splink(self):
        """使用 Splink 进行实体规范化（首选）"""
        try:
            import splink.comparison_library as cl
            from splink import Linker
        except ImportError:
            logger.warning("Splink 未安装，无法使用高级规范化")
            raise

        nodes = list(self.graph.nodes())
        if len(nodes) < 2:
            return

        df = pd.DataFrame({"entity_name": nodes})
        settings = {
            "link_type": "dedupe_only",
            "blocking_rules_to_generate_predictions": [Config.SPLINK_BLOCKING_RULE],
            "comparisons": [
                cl.LevenshteinAtThresholds("entity_name", threshold=Config.SPLINK_COMPARISON_LEVELS),
                cl.JaroWinklerAtThresholds("entity_name", threshold=Config.SPLINK_JARO_WINKLER_THRESHOLDS),
            ],
            "retain_intermediate_calculation_columns": False,
            "max_iterations": 10,
            "em_convergence": 0.01,
        }
        linker = Linker(df, settings, db_api="duckdb")
        df_predict = linker.predict().as_pandas_dataframe()

        clusters = df_predict.groupby("cluster_id")["entity_name"].apply(list).tolist()
        for cluster in clusters:
            if len(cluster) <= 1:
                continue
            keep = max(cluster, key=len)  # 保留最长的实体名（通常最完整）
            removes = [e for e in cluster if e != keep]
            for rem in removes:
                if keep not in self.entity_to_chunks:
                    self.entity_to_chunks[keep] = set()
                self.entity_to_chunks[keep].update(self.entity_to_chunks.get(rem, set()))
                for neighbor in list(self.graph.neighbors(rem)):
                    edge_data = self.graph.get_edge_data(rem, neighbor)
                    self.graph.add_edge(keep, neighbor, **(edge_data or {}))
                self.graph.remove_node(rem)
                if rem in self.entity_to_chunks:
                    del self.entity_to_chunks[rem]

    def normalize_entities(self):
        """实体规范化入口：优先 Splink，失败则回退到简单相似度"""
        try:
            self._normalize_by_splink()
            logger.info("实体规范化完成 (Splink)")
        except Exception as e:
            logger.warning(f"Splink 规范化失败: {e}，回退到简单相似度方法")
            self._normalize_simple()

    # ------ 加载 / 保存 ------
    def load(self):
        if os.path.exists(Config.GRAPH_FILE):
            try:
                with open(Config.GRAPH_FILE, "rb") as f:
                    data = pickle.load(f)
                if isinstance(data, tuple):
                    self.graph, self.entity_to_chunks = data
                else:
                    self.graph = data
                    self.entity_to_chunks = {}
                return True
            except Exception as e:
                logger.warning(f"加载图谱失败: {e}")
                return False
        return False

    # ------ 检索 ------
    def retrieve_by_entities(self, query: str, top_k=3) -> list[int]:
        prompt = f"从以下问题中提取出最重要的实体名词，只输出实体，多个用逗号分隔。不要输出其他内容。\n问题：{query}"
        try:
            resp = self._llm.generate(model=Config.LLM_MODEL, prompt=prompt)
            entities = [e.strip() for e in resp.split(",") if e.strip()]
        except Exception:
            entities = []
        if not entities:
            return []
        chunk_scores = {}
        for ent in entities:
            if ent in self.entity_to_chunks:
                for idx in self.entity_to_chunks[ent]:
                    chunk_scores[idx] = chunk_scores.get(idx, 0) + 1
        sorted_idx = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [idx for idx, _ in sorted_idx]

    def retrieve_by_entities_with_hops(self, query: str, hops: int = 1, top_k: int = 3) -> list[int]:
        prompt = f"从以下问题中提取出最重要的实体名词，只输出实体，多个用逗号分隔。不要输出其他内容。\n问题：{query}"
        try:
            resp = self._llm.generate(model=Config.TRIPLE_EXTRACT_MODEL, prompt=prompt)
            entities = [e.strip() for e in resp.split(",") if e.strip()]
        except Exception:
            entities = []
        if not entities:
            return []

        visited_entities = set()
        frontier = set(entities)
        for _ in range(hops + 1):
            new_frontier = set()
            for ent in frontier:
                if ent in visited_entities:
                    continue
                visited_entities.add(ent)
                if ent in self.graph:
                    for neighbor in self.graph.neighbors(ent):
                        new_frontier.add(neighbor)
            frontier = new_frontier

        chunk_scores = {}
        for ent in visited_entities:
            if ent in self.entity_to_chunks:
                for idx in self.entity_to_chunks[ent]:
                    chunk_scores[idx] = chunk_scores.get(idx, 0) + 1
        sorted_indices = sorted(chunk_scores.items(), key=lambda x: x[1], reverse=True)[:top_k]
        return [idx for idx, _ in sorted_indices]

    # ------ 可视化 ------
    def to_html(self, output_path: str = "knowledge_graph.html"):
        from pyvis.network import Network

        net = Network(height="600px", width="100%", bgcolor="#ffffff", font_color="black")
        for node in self.graph.nodes():
            net.add_node(node, label=node, title=node)
        for u, v, data in self.graph.edges(data=True):
            label = data.get("relation", "")
            net.add_edge(u, v, title=label, label=label)
        net.set_options("""
        var options = {
            "physics": {
                "enabled": true,
                "stabilization": {"iterations": 100}
            }
        }
        """)
        net.save_graph(output_path)
        return output_path
