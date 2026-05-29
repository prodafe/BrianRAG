"""BrianRAG 性能基准测试 — 检索延迟、答案质量评估"""

import contextlib
import json
import logging
import statistics
import time
from collections.abc import Sequence
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)

# ── 内置测试查询 ──
_DEFAULT_QUERIES = [
    "减震器结构设计要点是什么",
    "驱动轮与地面的作用力公式",
    "弹簧预压力的作用",
    "Flex调试需要哪些准备",
    "如何配置编译环境",
]


@dataclass
class BenchmarkResult:
    name: str
    total_queries: int
    latency_p50_ms: float
    latency_p95_ms: float
    latency_p99_ms: float
    latency_mean_ms: float
    latency_min_ms: float
    latency_max_ms: float
    details: list[dict] = field(default_factory=list)


def _percentiles(values: Sequence[float], *ps: float) -> dict[float, float]:
    if not values:
        return {p: 0 for p in ps}
    s = sorted(values)
    return {p: s[max(0, min(len(s) - 1, int(len(s) * p / 100)))] for p in ps}


def benchmark_retrieval(
    pipeline,
    queries: list[str] | None = None,
    warmup_runs: int = 2,
    runs: int = 5,
) -> BenchmarkResult:
    """测试检索延迟，返回 P50/P95/P99 等指标"""
    qs = queries or _DEFAULT_QUERIES
    all_latencies = []

    # Warmup
    for _ in range(warmup_runs):
        for q in qs:
            with contextlib.suppress(Exception):
                pipeline.retriever.hybrid_search(q)

    # Benchmark
    details = []
    for run in range(runs):
        for q in qs:
            try:
                t0 = time.perf_counter()
                texts, indices = pipeline.retriever.hybrid_search(q)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                all_latencies.append(elapsed_ms)
                details.append({
                    "run": run,
                    "query": q,
                    "latency_ms": round(elapsed_ms, 2),
                    "results": len(texts),
                })
            except Exception as e:
                logger.warning(f"检索失败 '{q}': {e}")
                details.append({"run": run, "query": q, "latency_ms": None, "error": str(e)})

    pct = _percentiles(all_latencies, 50, 95, 99)
    return BenchmarkResult(
        name="retrieval_latency",
        total_queries=len(all_latencies),
        latency_p50_ms=round(pct.get(50, 0), 2),
        latency_p95_ms=round(pct.get(95, 0), 2),
        latency_p99_ms=round(pct.get(99, 0), 2),
        latency_mean_ms=round(statistics.mean(all_latencies), 2) if all_latencies else 0,
        latency_min_ms=round(min(all_latencies), 2) if all_latencies else 0,
        latency_max_ms=round(max(all_latencies), 2) if all_latencies else 0,
        details=details,
    )


def benchmark_end_to_end(
    pipeline,
    queries: list[str] | None = None,
    runs: int = 3,
) -> BenchmarkResult:
    """端到端问答延迟测试"""
    qs = queries or _DEFAULT_QUERIES[:3]
    all_latencies = []

    details = []
    for run in range(runs):
        for q in qs:
            try:
                t0 = time.perf_counter()
                result = pipeline.query(q, history=None)
                elapsed_ms = (time.perf_counter() - t0) * 1000
                all_latencies.append(elapsed_ms)
                answer_len = len(result.get("answer", ""))
                cites = len(result.get("citations", {}))
                details.append({
                    "run": run, "query": q,
                    "latency_ms": round(elapsed_ms, 2),
                    "answer_chars": answer_len,
                    "citations": cites,
                })
            except Exception as e:
                logger.warning(f"问答失败 '{q}': {e}")
                details.append({"run": run, "query": q, "latency_ms": None, "error": str(e)})

    pct = _percentiles(all_latencies, 50, 95, 99)
    return BenchmarkResult(
        name="end_to_end",
        total_queries=len(all_latencies),
        latency_p50_ms=round(pct.get(50, 0), 2),
        latency_p95_ms=round(pct.get(95, 0), 2),
        latency_p99_ms=round(pct.get(99, 0), 2),
        latency_mean_ms=round(statistics.mean(all_latencies), 2) if all_latencies else 0,
        latency_min_ms=round(min(all_latencies), 2) if all_latencies else 0,
        latency_max_ms=round(max(all_latencies), 2) if all_latencies else 0,
        details=details,
    )


def benchmark_embedding(queries: list[str] | None = None, batch_sizes: list[int] | None = None) -> list[dict]:
    """测试嵌入吞吐量"""
    import ollama

    from config import Config

    qs = queries or ["测试查询文本"] * 10
    batches = batch_sizes or [1, 4, 8, 16]
    results = []

    for bs in batches:
        batch = qs[:bs]
        t0 = time.perf_counter()
        try:
            ollama.embed(model=Config.EMBEDDING_MODEL, input=batch)
            elapsed_ms = (time.perf_counter() - t0) * 1000
            results.append({"batch_size": bs, "latency_ms": round(elapsed_ms, 2), "per_item_ms": round(elapsed_ms / bs, 2)})
        except Exception as e:
            results.append({"batch_size": bs, "error": str(e)})

    return results


def run_all_benchmarks(pipeline=None, output_path: str | None = None) -> dict:
    """运行全部基准测试并返回结果"""
    results = {}

    if pipeline is None:
        logger.warning("pipeline 未提供，仅运行嵌入测试")
        results["embedding"] = benchmark_embedding()
    else:
        logger.info("开始检索延迟测试...")
        results["retrieval"] = benchmark_retrieval(pipeline).__dict__
        logger.info("开始端到端问答延迟测试...")
        results["end_to_end"] = benchmark_end_to_end(pipeline).__dict__

    results["embedding"] = benchmark_embedding()

    if output_path:
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        logger.info(f"基准测试结果已保存至 {output_path}")

    return results


if __name__ == "__main__":
    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

    logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")

    from core.rag_pipeline import RAGPipeline

    p = RAGPipeline()
    res = run_all_benchmarks(p, "evaluation/benchmark_results.json")

    print("\n═══ 检索延迟 ═══")
    if "retrieval" in res:
        r = res["retrieval"]
        print(f"  P50: {r['latency_p50_ms']}ms  P95: {r['latency_p95_ms']}ms  P99: {r['latency_p99_ms']}ms  Mean: {r['latency_mean_ms']}ms")
    print("\n═══ 端到端 ═══")
    if "end_to_end" in res:
        r = res["end_to_end"]
        print(f"  P50: {r['latency_p50_ms']}ms  P95: {r['latency_p95_ms']}ms  Mean: {r['latency_mean_ms']}ms")
    print("\n═══ 嵌入吞吐量 ═══")
    for e in res.get("embedding", []):
        print(f"  batch={e['batch_size']}: {e.get('latency_ms', 'ERR')}ms ({e.get('per_item_ms', '?')}ms/item)")
