"""
Prometheus 指标收集模块
用于监控 RAG 系统的请求数、延迟、检索文档数、LLM 调用次数、Token 消耗、缓存命中率等。
"""

from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import Response
import time
from functools import wraps
from typing import Callable, Any

# ==================== 指标定义 ====================
REQUESTS = Counter("rag_requests_total", "Total number of requests", ["endpoint", "mode"])

REQUEST_DURATION = Histogram("rag_request_duration_seconds", "Request latency in seconds", ["endpoint"])

RETRIEVAL_DOCS = Histogram("rag_retrieved_docs_count", "Number of retrieved documents per query", ["mode"])

LLM_CALLS = Counter("rag_llm_calls_total", "Total number of LLM invocations", ["model", "operation"])

LLM_TOKENS = Counter(
    "rag_llm_tokens_total",
    "Total tokens consumed by LLM",
    ["model", "type"],  # type: 'prompt' or 'completion'
)

CACHE_HITS = Counter("rag_cache_hits_total", "Number of cache hits")

CACHE_MISSES = Counter("rag_cache_misses_total", "Number of cache misses")

VISION_CALLS = Counter("rag_vision_calls_total", "Number of vision model invocations")

ACTIVE_TASKS = Gauge("rag_active_tasks", "Number of currently active Celery tasks")


# ==================== 辅助函数 ====================
def track_request(endpoint: str, mode: str = "unknown") -> Callable:
    """
    装饰器：自动记录请求计数和耗时。
    用法：
        @app.post("/api/query")
        @track_request(endpoint="/api/query", mode="rag")
        async def query_handler():
            ...
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            start = time.perf_counter()
            REQUESTS.labels(endpoint=endpoint, mode=mode).inc()
            try:
                result = await func(*args, **kwargs)
                return result
            finally:
                duration = time.perf_counter() - start
                REQUEST_DURATION.labels(endpoint=endpoint).observe(duration)

        return wrapper

    return decorator


def record_retrieval(mode: str, doc_count: int) -> None:
    """记录检索返回的文档数量"""
    RETRIEVAL_DOCS.labels(mode=mode).observe(doc_count)


def record_llm_call(model: str, operation: str, prompt_tokens: int = 0, completion_tokens: int = 0) -> None:
    """记录 LLM 调用次数和 Token 消耗"""
    LLM_CALLS.labels(model=model, operation=operation).inc()
    if prompt_tokens:
        LLM_TOKENS.labels(model=model, type="prompt").inc(prompt_tokens)
    if completion_tokens:
        LLM_TOKENS.labels(model=model, type="completion").inc(completion_tokens)


def record_cache_hit() -> None:
    """记录缓存命中"""
    CACHE_HITS.inc()


def record_cache_miss() -> None:
    """记录缓存未命中"""
    CACHE_MISSES.inc()


def record_vision_call() -> None:
    """记录视觉模型调用"""
    VISION_CALLS.inc()


def update_active_tasks(count: int) -> None:
    """更新当前活跃的 Celery 任务数"""
    ACTIVE_TASKS.set(count)


async def metrics_endpoint() -> Response:
    """
    FastAPI 端点：暴露 Prometheus 格式的指标。
    在 main.py 中挂载：app.add_route("/metrics", metrics_endpoint)
    """
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
