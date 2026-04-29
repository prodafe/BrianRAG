# # config.example.py - BrianRAG 配置文件模板
# # 使用说明：
# # 1. 复制本文件为 config.py
# # 2. 根据实际环境和需求修改各项配置
# # 3. 确保必要的目录存在（或调用 Config.ensure_dirs() 自动创建）
#
# import os
#
#
# class Config:
#     # ==================== 基础路径 ====================
#     BASE_DIR = os.path.dirname(os.path.abspath(__file__))
#
#     # 数据存储目录
#     DATA_DIR = os.path.join(BASE_DIR, "data")  # 上传的原始文档
#     INDEX_DIR = os.path.join(BASE_DIR, "index")  # FAISS 索引、BM25、图谱等
#     CACHE_DIR = os.path.join(BASE_DIR, "cache")  # 语义缓存、答案缓存
#     LOG_DIR = os.path.join(BASE_DIR, "logs")  # 日志文件目录
#     IMAGES_DIR = os.path.join(BASE_DIR, "data", "images")  # 从文档提取的图片
#
#     # 元数据文件
#     DOC_META_FILE = os.path.join(INDEX_DIR, "doc_meta.json")
#
#     # ==================== 检索参数 ====================
#     TOP_K = 5  # 最终返回的文本块数量
#     ALPHA = 0.5  # BM25 权重 (0~1)，向量权重为 1-ALPHA
#     SCORE_THRESHOLD = 0.3  # 相似度阈值，低于此值的结果被过滤
#
#     # ==================== 模型配置 (Ollama) ====================
#     OLLAMA_BASE_URL = "http://localhost:11434"  # Ollama 服务地址
#
#     # 嵌入模型
#     EMBEDDING_BINDING = "ollama"
#     EMBEDDING_MODEL = "bge-m3:latest"
#     EMBEDDING_DIM = 1024  # bge-m3 维度为 1024，与模型匹配
#
#     # 生成模型 (LLM)
#     LLM_MODEL = "qwen2.5:7b"  # 主对话模型，需先 ollama pull
#
#     # 视觉模型（多模态图片描述）
#     VISION_MODEL = "qwen2.5-vl:7b"
#
#     # 轻量模型（三元组提取、实体识别等）
#     TRIPLE_EXTRACT_MODEL = "qwen2.5:3b"
#
#     # ==================== 文本切片 ====================
#     CHUNK_SIZE = 500  # 每个文本块的最大字符数
#     CHUNK_OVERLAP = 50  # 相邻块之间的重叠字符数
#
#     # ==================== 知识图谱 ====================
#     ENABLE_GRAPH = True  # 是否启用知识图谱增强检索
#     GRAPH_FILE = os.path.join(INDEX_DIR, "knowledge_graph.gpickle")
#
#     # 图谱检索跳数（0=仅直接实体，1=包含一跳邻居）
#     GRAPH_HOPS = 1
#
#     # 实体规范化（合并相似实体）
#     ENABLE_ENTITY_NORMALIZATION = True
#     SPLINK_BLOCKING_RULE = "l.entity_name = r.entity_name"
#     SPLINK_COMPARISON_LEVELS = [2, 5]  # Levenshtein 阈值
#     SPLINK_JARO_WINKLER_THRESHOLDS = [0.9, 0.95]  # Jaro-Winkler 阈值
#
#     # ==================== 重排序 (Reranker) ====================
#     ENABLE_RERANK = True
#     # 重排序模型路径（本地绝对值或相对路径）
#     RERANK_MODEL = "D:/models/bge-reranker-v2-m3"  # 或 "./bge-reranker-v2-m3"
#     RERANK_USE_FP16 = True  # GPU 可用时启用 FP16 加速
#     RERANK_TOP_K = 3  # 重排序后保留的片段数
#     RERANK_CANDIDATE_MULTIPLIER = 2  # 候选数 = TOP_K * 该值，上限20
#
#     # ==================== 自我修正 (Self-Correction) ====================
#     ENABLE_SELF_CORRECTION = True
#     SELF_CORRECTION_MAX_RETRIES = 2
#     SELF_CORRECTION_SCORE_THRESHOLD = 0.6
#
#     # ==================== 查询优化 ====================
#     ENABLE_QUERY_REWRITE = True  # 启用查询改写
#     ENABLE_HYDE = True  # 启用 HyDE（假设文档嵌入）
#     HYDE_TOP_K = 5  # HyDE 生成的假设文档检索时使用的 top_k
#
#     # ==================== 多模态智能体 ====================
#     ENABLE_MULTIMODAL = True  # 启用多模态智能体模式（需安装 langgraph）
#
#     # ==================== 缓存 ====================
#     ENABLE_CACHE = True  # 启用语义缓存
#     CACHE_SIMILARITY_THRESHOLD = 0.95
#
#     # ==================== 多轮对话 ====================
#     MAX_HISTORY_TURNS = 5  # 保留的对话轮数（用户+助手）
#
#     # ==================== 性能优化 ====================
#     EMBED_BATCH_SIZE = 16  # 嵌入生成时的批次大小（根据内存/显存调整）
#
#     # ==================== 日志与监控 ====================
#     LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR
#     LOG_FILE = "logs/brianrag.log"
#     LOG_MAX_BYTES = 10 * 1024 * 1024  # 10MB
#     LOG_BACKUP_COUNT = 5
#
#     # ==================== 高级/实验功能 ====================
#     ENABLE_METRICS = False  # 是否启用 Prometheus 指标端点
#     METRICS_PORT = 8000  # Prometheus 指标端口
#
#     # ==================== 路径辅助方法 ====================
#     @classmethod
#     def ensure_dirs(cls):
#         """确保所有必要的目录存在"""
#         for d in [cls.DATA_DIR, cls.INDEX_DIR, cls.CACHE_DIR, cls.LOG_DIR, cls.IMAGES_DIR]:
#             os.makedirs(d, exist_ok=True)