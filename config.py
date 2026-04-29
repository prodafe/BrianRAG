import os

class Config:
    # 路径
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))
    DATA_DIR = os.path.join(BASE_DIR, "data")
    INDEX_DIR = os.path.join(BASE_DIR, "index")
    CACHE_DIR = os.path.join(BASE_DIR, "cache")
    LOG_DIR = os.path.join(BASE_DIR, "log")
    IMAGES_DIR = os.path.join(BASE_DIR, "data", "images")
    DOC_META_FILE = os.path.join(INDEX_DIR, "doc_meta.json")

    # 检索
    TOP_K = 5
    # TOP_K = 20
    ALPHA = 0.5
    SCORE_THRESHOLD = 0.3
    # SCORE_THRESHOLD = 0.1

    # 重排序配置
    ENABLE_RERANK = True
    # ENABLE_RERANK = False
    RERANK_MODEL = "D:/reranker/bge-reranker-v2-m3"  # 升级模型
    RERANK_USE_FP16 = True  # 如果GPU支持
    RERANK_TOP_K = 3
    RERANK_CANDIDATE_MULTIPLIER = 2


    # 嵌入模型
    EMBEDDING_BINDING = "ollama"
    EMBEDDING_MODEL = "bge-m3:latest"
    EMBEDDING_DIM = 1024  # bge-m3 的维度是 1024
    EMBEDDING_BINDING_HOST = "http://localhost:11434"

    # 生成模型
    LLM_MODEL = "qwen2.5:7b"
    OLLAMA_BASE_URL = "http://localhost:11434"

    # 切片
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50



    # 图谱
    ENABLE_GRAPH = False          # 是否启用图谱增强
    GRAPH_FILE = os.path.join(INDEX_DIR, "knowledge_graph.gpickle")

    # 知识图谱检索跳数（0 = 只检索直接实体，1 = 包括一跳邻居）
    GRAPH_HOPS = 1



    # 知识图谱三元组提取专用模型（轻量、快速）
    TRIPLE_EXTRACT_MODEL = "qwen2.5:7b"  # 可改为 "llama3.2:3b" 或其他


    # 缓存
    ENABLE_CACHE = True
    CACHE_SIMILARITY_THRESHOLD = 0.95

    # 多轮对话配置
    MAX_HISTORY_TURNS = 5  # 保留最近几轮对话（用户+助手）

    # ========== 性能优化配置 ==========
    EMBED_BATCH_SIZE = 16  # 嵌入生成时的批量大小（可根据内存调整，最大建议32）


    #视觉模型
    VISION_MODEL = "qwen2.5vl:7b"

    # Self-Correction 配置
    ENABLE_SELF_CORRECTION = False
    SELF_CORRECTION_MAX_RETRIES = 2
    # 评估阈值（0-1），低于此值触发修正
    SELF_CORRECTION_SCORE_THRESHOLD = 0.6

    # 实体规范化配置
    ENABLE_ENTITY_NORMALIZATION = False  # 是否启用实体规范化（Splink）
    SPLINK_BLOCKING_RULE = "l.entity_name = r.entity_name"  # 分块规则，可根据需要调整
    SPLINK_COMPARISON_LEVELS = [2, 5]  # Levenshtein 距离阈值
    SPLINK_JARO_WINKLER_THRESHOLDS = [0.9, 0.95]  # Jaro-Winkler 阈值

    TUNE_ENABLED = False
    TUNE_PARAM_GRID = {
        "alpha": [0.3, 0.5, 0.7, 0.9],
        "top_k": [3, 5, 7],
        "score_threshold": [0.2, 0.3, 0.4]
    }

    # 日志配置
    LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
    LOG_FILE = "logs/brianrag.log"
    LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
    LOG_BACKUP_COUNT = 5

    # 查询优化配置
    ENABLE_QUERY_REWRITE = True  # 是否启用查询改写
    # ENABLE_QUERY_REWRITE = False
    ENABLE_HYDE = True  # 是否启用 HyDE
    # ENABLE_HYDE = False
    HYDE_TOP_K = 5  # HyDE 生成的假设文档参与检索时的 top_k

    # ==================== 数据库配置 ====================
    # PostgreSQL 连接字符串（请根据你的实际路径和认证信息修改）
    # 格式：postgresql://[user[:password]@][host][:port][/database]
    DATABASE_URL = "postgresql+psycopg://postgres:123456@localhost:5432/postgres"
    ASYNC_DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://")
    # 向量存储表名
    VECTOR_TABLE_NAME = "brianrag_vectors"

    # 混合检索权重：向量检索权重 = 1 - ALPHA（与 BM25 融合时使用）
    # 我们仍然使用 Config.ALPHA 作为 BM25 权重，向量权重为 1 - ALPHA

    # ==================== 向量索引优化 ====================
    # HNSW 索引参数
    VECTOR_INDEX_TYPE = "HNSW"
    VECTOR_HNSW_M = 32  # 每层最大连接数
    VECTOR_HNSW_EF_CONSTRUCTION = 200  # 构建时动态列表大小

    # ==================== 检索性能 ====================
    HYBRID_SEARCH_WORKERS = 3  # 并行检索线程数（向量 + BM25 + 图谱）
    VECTOR_HNSW_EF_SEARCH = 100  # 查询时动态列表大小


    CHROMA_PERSIST_DIR = os.path.join(BASE_DIR, "chroma_db")


    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    ENABLE_CONTEXT_EXPANSION = True
    # ENABLE_CONTEXT_EXPANSION = False

    ENABLE_SECONDARY_RETRIEVAL = True  # 是否启用二次检索
    # ENABLE_SECONDARY_RETRIEVAL = False
    SECONDARY_RETRIEVAL_THRESHOLD = 0.65  # 最高分低于此阈值时触发4

    # 上下文扩展配置
    CONTEXT_EXPANSION_BEFORE = 1  # 向前扩展块数
    CONTEXT_EXPANSION_AFTER = 1  # 向后扩展块数

    # 意图识别权重配置
    INTENT_WEIGHT_FORMULA = 1.2
    INTENT_WEIGHT_DEFINITION = 1.2
    INTENT_WEIGHT_PROCEDURE = 1.2

    @classmethod
    def ensure_dirs(cls):
        for d in [cls.DATA_DIR, cls.INDEX_DIR, cls.CACHE_DIR, cls.LOG_DIR, cls.IMAGES_DIR]:
            os.makedirs(d, exist_ok=True)

