"""BrianRAG 配置 — pydantic-settings，自动从 .env / 环境变量加载"""

import contextlib
import os
import threading

try:
    from pydantic_settings import BaseSettings
except ImportError:
    # 回退：无 pydantic-settings 时使用纯 Python 类
    BaseSettings = object

_BASE_DIR = os.path.dirname(os.path.abspath(__file__))

if BaseSettings is not object:

    class _Settings(BaseSettings):
        model_config = {"env_prefix": "BRIAN_", "env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

        def __getattr__(self, name: str):
            """向下兼容 UPPER_CASE 属性名 → 自动映射到 lower_case"""
            if name.isupper() and not name.startswith("_"):
                lower = name.lower()
                if lower in self.model_fields:
                    return getattr(self, lower)
            raise AttributeError(f"{type(self).__name__!r} object has no attribute {name!r}")

        def __setattr__(self, name: str, value):
            """向下兼容 UPPER_CASE 赋值 → 映射到 lower_case 字段"""
            if name.isupper() and not name.startswith("_"):
                lower = name.lower()
                if lower in self.model_fields:
                    object.__setattr__(self, lower, value)
                    return
            object.__setattr__(self, name, value)

        # ── 路径 ──
        base_dir: str = _BASE_DIR
        data_dir: str = os.path.join(_BASE_DIR, "data")
        index_dir: str = os.path.join(_BASE_DIR, "index")
        cache_dir: str = os.path.join(_BASE_DIR, "cache")
        log_dir: str = os.path.join(_BASE_DIR, "logs")
        images_dir: str = os.path.join(_BASE_DIR, "data", "images")
        doc_meta_file: str = os.path.join(_BASE_DIR, "index", "doc_meta.json")

        # ── 检索 ──
        top_k: int = 5
        alpha: float = 0.5
        score_threshold: float = 0.3
        enable_mmr: bool = True
        mmr_lambda: float = 0.7

        # ── 重排序 ──
        enable_rerank: bool = True
        rerank_model: str = "BAAI/bge-reranker-v2-m3"
        rerank_use_fp16: bool = True
        rerank_top_k: int = 3
        rerank_candidate_multiplier: int = 2

        # ── 超时（秒）──
        llm_generate_timeout: int = 120
        llm_stream_timeout: int = 300
        embedding_timeout: int = 60
        vision_timeout: int = 120
        graph_normalize_timeout: int = 300

        # ── 嵌入 ──
        embedding_binding: str = "ollama"
        embedding_model: str = "bge-m3:latest"
        embedding_dim: int = 1024
        embedding_binding_host: str = "http://localhost:11434"

        # ── LLM Provider ──
        llm_provider: str = "ollama"
        llm_model: str = "qwen2.5:7b"
        ollama_base_url: str = "http://localhost:11434"
        llm_api_key: str = ""
        evaluator_model: str = "qwen2.5:1.5b"

        # ── 文档切片 ──
        chunk_size: int = 800
        chunk_overlap: int = 100
        enable_semantic_chunking: bool = True
        semantic_chunk_threshold: float = 0.45

        # ── 知识图谱 ──
        enable_graph: bool = True
        graph_file: str = os.path.join(_BASE_DIR, "index", "knowledge_graph.gpickle")
        graph_hops: int = 1
        triple_extract_model: str = "qwen2.5:7b"

        # ── 缓存 ──
        enable_cache: bool = True
        cache_similarity_threshold: float = 0.95
        max_history_turns: int = 5

        # ── 性能 ──
        embed_batch_size: int = 16
        hybrid_search_workers: int = 3
        vision_workers: int = 4
        vector_hnsw_ef_search: int = 100

        # ── 视觉 ──
        vision_model: str = "qwen2.5vl:7b"

        # ── 自我修正 ──
        enable_self_correction: bool = True
        self_correction_max_retries: int = 2
        self_correction_score_threshold: float = 0.6

        # ── 实体规范化 ──
        enable_entity_normalization: bool = True
        splink_blocking_rule: str = "l.entity_name = r.entity_name"
        splink_comparison_levels: list = [1, 2]
        splink_jaro_winkler_thresholds: list = [0.9, 0.95]

        # ── 查询优化 ──
        enable_query_rewrite: bool = True
        enable_hyde: bool = True
        hyde_top_k: int = 5
        enable_multi_query: bool = True
        enable_synonym_expansion: bool = True

        # ── 数据库 ──
        database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
        vector_table_name: str = "brianrag_vectors"
        vector_index_type: str = "HNSW"
        vector_hnsw_m: int = 48
        vector_hnsw_ef_construction: int = 200

        @property
        def async_database_url(self) -> str:
            return self.database_url.replace("+psycopg://", "+asyncpg://").replace(
                "postgresql://", "postgresql+asyncpg://"
            )

        # ── Chroma (备用) ──
        chroma_persist_dir: str = os.path.join(_BASE_DIR, "chroma_db")

        # ── Redis ──
        redis_url: str = "redis://localhost:6379/0"

        # ── 上下文扩展 ──
        enable_context_expansion: bool = True
        enable_secondary_retrieval: bool = True
        secondary_retrieval_threshold: float = 0.65
        context_expansion_before: int = 1
        context_expansion_after: int = 1

        # ── 检索门控 ──
        enable_retrieval_gating: bool = True
        gating_score_threshold: float = 0.35
        gating_max_retries: int = 2
        gating_knowledge_gap_response: str = "该问题超出当前知识库范围，建议补充相关文档或换个问法。"

        # ── GitHub 数据源 ──
        github_repo_url: str = ""
        github_branch: str = "main"
        github_token: str = ""
        github_local_path: str = os.path.join(_BASE_DIR, "data", "github_repo")
        github_sync_interval: int = 300
        github_doc_patterns: list = ["*.md", "*.txt", "*.pdf", "*.docx", "*.html", "*.csv"]

        # ── 意图识别 ──
        intent_weight_formula: float = 1.2
        intent_weight_definition: float = 1.2
        intent_weight_procedure: float = 1.2
        dynamic_alpha: bool = True
        enable_intent_weighting: bool = True

        # ── 多模态 ──
        enable_multimodal: bool = True
        multimodal_model_path: str = "sentence-transformers/clip-ViT-B-32-multilingual-v1"
        multimodal_device: str = "cuda"
        multimodal_similarity_threshold: float = 0.7
        multimodal_top_k: int = 3
        multimodal_fusion_weight: float = 0.3

        # ── 前端/图片 ──
        fe_domain: str = "http://localhost:8000"
        images_url_prefix: str = "/images"
        process_missing_images: bool = True

        # ── 可观测性 ──
        enable_telemetry: bool = True
        otlp_endpoint: str = "http://localhost:4318/v1/traces"
        enable_metrics: bool = True

        # ── 日志 ──
        log_level: str = "INFO"
        log_file: str = "logs/brianrag.log"
        log_max_bytes: int = 10 * 1024 * 1024
        log_backup_count: int = 5

        # ── 热点问题 ──
        hot_question_threshold: int = 20
        hot_question_ttl: int = 7 * 24 * 3600
        hot_question_prewarm_interval: int = 3600

        # ── 预训练 ──
        prewarm_question_count: int = 150
        prewarm_similarity_threshold: float = 0.72

        # ── 调优 ──
        tune_enabled: bool = False
        tune_param_grid: dict = {
            "alpha": [0.3, 0.5, 0.7, 0.9],
            "top_k": [3, 5, 7],
            "score_threshold": [0.2, 0.3, 0.4],
        }

    Config = _Settings()
else:
    # 回退：纯 Python Config（功能相同，无验证）
    class _Config:
        def __init__(self):
            self.base_dir = _BASE_DIR
            self.data_dir = os.path.join(_BASE_DIR, "data")
            self.index_dir = os.path.join(_BASE_DIR, "index")
            self.cache_dir = os.path.join(_BASE_DIR, "cache")
            self.log_dir = os.path.join(_BASE_DIR, "logs")
            self.images_dir = os.path.join(_BASE_DIR, "data", "images")
            self.doc_meta_file = os.path.join(_BASE_DIR, "index", "doc_meta.json")
            self.top_k = 5
            self.alpha = 0.5
            self.score_threshold = 0.3
            self.enable_mmr = True
            self.mmr_lambda = 0.7
            self.enable_rerank = True
            self.rerank_model = "BAAI/bge-reranker-v2-m3"
            self.rerank_use_fp16 = True
            self.rerank_top_k = 3
            self.rerank_candidate_multiplier = 2
            self.embedding_binding = "ollama"
            self.embedding_model = "bge-m3:latest"
            self.embedding_dim = 1024
            self.embedding_binding_host = "http://localhost:11434"
            self.llm_generate_timeout = 120
            self.llm_stream_timeout = 300
            self.embedding_timeout = 60
            self.vision_timeout = 120
            self.graph_normalize_timeout = 300
            self.llm_provider = "ollama"
            self.llm_model = "qwen2.5:7b"
            self.ollama_base_url = "http://localhost:11434"
            self.llm_api_key = ""
            self.evaluator_model = "qwen2.5:1.5b"
            self.chunk_size = 800
            self.chunk_overlap = 100
            self.enable_semantic_chunking = True
            self.semantic_chunk_threshold = 0.45
            self.enable_graph = True
            self.graph_file = os.path.join(_BASE_DIR, "index", "knowledge_graph.gpickle")
            self.graph_hops = 1
            self.triple_extract_model = "qwen2.5:7b"
            self.enable_cache = True
            self.cache_similarity_threshold = 0.95
            self.max_history_turns = 5
            self.embed_batch_size = 16
            self.hybrid_search_workers = 3
            self.vision_workers = 4
            self.vector_hnsw_ef_search = 100
            self.vision_model = "qwen2.5vl:7b"
            self.enable_self_correction = True
            self.self_correction_max_retries = 2
            self.self_correction_score_threshold = 0.6
            self.enable_entity_normalization = True
            self.splink_blocking_rule = "l.entity_name = r.entity_name"
            self.splink_comparison_levels = [1, 2]
            self.splink_jaro_winkler_thresholds = [0.9, 0.95]
            self.enable_query_rewrite = True
            self.enable_hyde = True
            self.hyde_top_k = 5
            self.enable_multi_query = True
            self.enable_synonym_expansion = True
            self.database_url = os.getenv(
                "DATABASE_URL", "postgresql+psycopg://postgres:postgres@localhost:5432/postgres"
            )
            self.vector_table_name = "brianrag_vectors"
            self.vector_index_type = "HNSW"
            self.vector_hnsw_m = 48
            self.vector_hnsw_ef_construction = 200
            self.chroma_persist_dir = os.path.join(_BASE_DIR, "chroma_db")
            self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.enable_context_expansion = True
            self.enable_secondary_retrieval = True
            self.secondary_retrieval_threshold = 0.65
            self.context_expansion_before = 1
            self.context_expansion_after = 1
            self.enable_retrieval_gating = True
            self.gating_score_threshold = 0.35
            self.gating_max_retries = 2
            self.gating_knowledge_gap_response = "该问题超出当前知识库范围，建议补充相关文档或换个问法。"
            self.github_repo_url = ""
            self.github_branch = "main"
            self.github_token = ""
            self.github_local_path = os.path.join(_BASE_DIR, "data", "github_repo")
            self.github_sync_interval = 300
            self.github_doc_patterns = ["*.md", "*.txt", "*.pdf", "*.docx", "*.html", "*.csv"]
            self.intent_weight_formula = 1.2
            self.intent_weight_definition = 1.2
            self.intent_weight_procedure = 1.2
            self.dynamic_alpha = True
            self.enable_intent_weighting = True
            self.enable_multimodal = True
            self.multimodal_model_path = ""
            self.multimodal_device = "cuda"
            self.multimodal_similarity_threshold = 0.7
            self.multimodal_top_k = 3
            self.multimodal_fusion_weight = 0.3
            self.fe_domain = "http://localhost:8000"
            self.images_url_prefix = "/images"
            self.process_missing_images = True
            self.enable_telemetry = True
            self.otlp_endpoint = "http://localhost:4318/v1/traces"
            self.enable_metrics = True
            self.log_level = "INFO"
            self.log_file = "logs/brianrag.log"
            self.log_max_bytes = 10 * 1024 * 1024
            self.log_backup_count = 5
            self.hot_question_threshold = 20
            self.hot_question_ttl = 7 * 24 * 3600
            self.hot_question_prewarm_interval = 3600
            self.prewarm_question_count = 150
            self.prewarm_similarity_threshold = 0.72
            self.tune_enabled = False
            self.tune_param_grid = {
                "alpha": [0.3, 0.5, 0.7, 0.9],
                "top_k": [3, 5, 7],
                "score_threshold": [0.2, 0.3, 0.4],
            }

        @property
        def async_database_url(self):
            return self.database_url.replace("+psycopg://", "+asyncpg://").replace(
                "postgresql://", "postgresql+asyncpg://"
            )

    Config = _Config()

# 加载 .env 文件（无 pydantic-settings 时的手动回退）
if BaseSettings is object:
    _env_path = os.path.join(_BASE_DIR, ".env")
    if os.path.exists(_env_path):
        with open(_env_path, encoding="utf-8") as _f:
            for _line in _f:
                _line = _line.strip()
                if _line and not _line.startswith("#") and "=" in _line:
                    _key, _val = _line.split("=", 1)
                    _key, _val = _key.strip(), _val.strip().strip('"').strip("'")
                    if _key.startswith("BRIAN_"):
                        _attr = _key[6:].lower()
                        if hasattr(Config, _attr):
                            _cur = getattr(Config, _attr)
                            _val = type(_cur)(_val) if not isinstance(_cur, bool) else _val.lower() == "true"
                            setattr(Config, _attr, _val)

# 兼容旧代码：_Settings.__getattr__ 自动将 UPPER_CASE 映射到 lower_case


# ── 线程安全的临时配置覆写 ──
_SENTINEL = object()
_overrides = threading.local()


@contextlib.contextmanager
def config_override(**kwargs):
    """线程安全的临时配置覆写。

    Usage:
        with config_override(alpha=0.3, enable_multimodal=False):
            pipeline.query("...")
    """
    saved = {}
    for k in kwargs:
        saved[k] = getattr(_overrides, k, _SENTINEL)
        setattr(_overrides, k, kwargs[k])
    try:
        yield
    finally:
        for k, prev in saved.items():
            if prev is _SENTINEL:
                try:
                    delattr(_overrides, k)
                except AttributeError:
                    pass
            else:
                setattr(_overrides, k, prev)


def _get_config(name: str):
    """读取配置值，优先使用当前线程的覆写。"""
    v = getattr(_overrides, name, _SENTINEL)
    if v is not _SENTINEL:
        return v
    return getattr(Config, name, getattr(Config, name.upper(), None))
