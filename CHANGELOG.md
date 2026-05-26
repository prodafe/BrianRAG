# Changelog

## [1.0.0] — 2026-05-26

### 新增
- FastAPI REST API（替代 Streamlit）
- Three.js + GSAP 着陆页（8 场景摄像机滚动）
- 流式 SSE 问答（marked.js + KaTeX 渲染）
- pgvector HNSW 向量存储（替代 FAISS）
- LLM Provider 可插拔抽象层（Ollama / OpenAI / Anthropic）
- 预训练缓存系统（Prewarm Engine）
- GitHub 数据源集成（clone + pull + 增量索引）
- RAGAS 评估回路
- 检索门控 + 降级策略（HyDE fallback）
- 文档语义分块（bge-m3 相似度边界检测）
- 模型层性能优化（批量查询优化：4 次 LLM 调用 → 1 次）
- pydantic-settings 配置管理
- 后台任务系统（asyncio.create_task 替代 Celery）
- API Key 鉴权中间件
- 进度指示点 + 键盘导航
- 停止生成按钮 + Esc 取消
- 友好错误提示

### 修复
- self_correction.py / graph_builder.py LLM 返回类型不匹配
- agents.py HTML 表格标签错误
- generator.py 缓存丢失 citation 数据
- ASYNC_DATABASE_URL regex 不匹配
- query_optimizer.py 相对路径
- 上传路径穿越漏洞
- APScheduler 不关闭导致僵尸线程
- HNSW 索引参数硬编码与 Config 不一致
- 移除未使用的 streamlit import
- requirements.txt 去重补缺

### 架构优化
- Config → pydantic-settings（类型验证 + .env 加载）
- Celery → asyncio 后台任务（ThreadPoolExecutor）
- Health check 5 秒缓存
- 速率限制 10/min → 60/min
- 延迟初始化 agentic_graph retriever
- SQLAlchemy 2.0 兼容 import
