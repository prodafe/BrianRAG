# Changelog

## [2.1.0] — 2026-05-28

### 修复 (Bug Fixes)
- 修复 `@app.get()@limiter.limit()` 装饰器单行语法（第二个 `@` 被解析为矩阵乘法）
- 修复 `_bg_executor` 未 shutdown（僵尸线程泄漏）
- 修复 `core/prewarm.py` 裸 `except:` → 具体异常类型
- 修复 `utils/document_loader.py` 无文件权限检查
- 修复前端 `event` 全局变量 + 重复发送保护
- 修复 `_table_aware_split` 表格重复切分 Bug

### 新增 (Features)

**Memory 系统** — 用户级记忆 Redis 持久化，跨会话上下文，LLM 自动信息提取

**父子分块 + Table-aware** — Parent-Child Chunking，表格不切断

**GraphRAG 社区摘要** — Leiden/Louvain 社区检测 + LLM 社区摘要生成

**Agent 工作流引擎** — JSON 定义 DAG，4 节点类型（检索/生成/工具/条件），2 内置模板

**多 Agent 协作** — Planner→Retriever→Critic 三角色编排 + 反思改进循环

**Agent 工具扩展（4→7）** — 代码沙箱 + HTTP API 调用 + 文件读取

**多 LLM Provider 自动检测** — 自动检测 `OPENAI_API_KEY`/`ANTHROPIC_API_KEY`

**数据源连接器（1→20）** — Notion/S3/Confluence/GoogleDrive/WebDAV/RSS/Jira/Slack/Discord/GitLab/Dropbox/OneDrive/Asana/Trello/Airtable/钉钉/飞书/IMAP + TOC 提取

**查询分解** — 复杂问题→子查询→并行检索→LLM 合并

**PDF/文档增强** — PyMuPDF 原生表格提取→Markdown，VLM 图片 Caption

**前端全面升级** — CSS/JS 模块化，60 键中英双语 i18n，独立管理后台（admin.html），PWA + Service Worker

**RAGAS 自动化** — 一键评估 + 历史对比 + 检索延迟 P50/P95/P99 基准测试

**文档站** — `docs/API.md`、`docs/GUIDE.md`、`docs/DEPLOY.md`

**社区建设** — `.github/CODEOWNERS`、`FUNDING.yml`、`PULL_REQUEST_TEMPLATE.md`

### 测试: 66 → 184 (+118 tests, 16 新测试模块)

---

## [2.0.0] — 2026-05-26

### 架构升级
- **FastAPI** 替代 Streamlit（端口 8000）
- **pydantic-settings** 替代手写 Config 类（类型验证 + `.env` 自动加载）
- **Celery 移除** → `asyncio` + `ThreadPoolExecutor` 后台任务
- **pgvector HNSW** 向量存储替代 FAISS
- **LLM Provider 可插拔抽象层**：一行配置切换 Ollama / OpenAI / Anthropic

### 新增功能

**检索 & 推理**
- 三路 RRF 混合检索（BM25 + 向量 + 知识图谱）+ MMR 去重
- 检索质量门控 + 降级策略（放宽检索 → HyDE → 知识缺口响应）
- 批量查询优化：4 次 LLM 调用合并为 1 次
- 工具调用系统（calc 计算器 / time 时间 / unit 单位换算）
- 多轮对话全链路打通
- LangGraph 多步迭代 RAG 工作流 + ReAct Agent

**文档处理**
- PDF 版式分析器（多栏检测 / 阅读顺序 / 表格识别 / 标题层级 / 图片提取）
- OCR 扫描件支持（PaddleOCR + Tesseract 双引擎）
- 章节感知切分（`##` / `###`）+ 语义分块（bge-m3 相似度边界检测）
- Loader 插件注册表（`@register_loader(['.xyz'])` 自定义解析器）
- 支持 17 种文档格式（md / pdf / docx / html / csv / pptx / xlsx / 图片等）

**前端**
- Three.js + GSAP 3D 着陆页（8 场景摄像机滚动 + 场景进度点 + 键盘导航）
- SSE 流式问答（marked.js + KaTeX 完整 Markdown/公式渲染）
- 停止生成按钮 + Esc 取消 + 分阶段加载指示
- 友好错误提示（中文映射）

**平台 & 安全**
- 多租户 + RBAC 权限系统（admin / editor / viewer 三种角色）
- 会话管理（Redis 存储，7 天 TTL）
- WebSocket 实时索引进度推送
- API Key 鉴权中间件 + 多租户 API Key 模式
- 预训练缓存系统（Prewarm Engine）
- GitHub 数据源集成（clone + pull + 变更检测 + 增量索引）
- RAGAS 评估回路

### 工程提升
- 46 tests，5 核心模块覆盖（pytest + cov）
- GitHub Actions CI（ruff lint + mypy typecheck + pytest, 3 个 Python 版本）
- pre-commit hooks（ruff format + lint + mypy）
- pyproject.toml 标准打包 + `pip install -e ".[dev]"`
- Type hints 覆盖 5 个核心模块 + `py.typed`（PEP 561）
- ruff format 全项目统一格式化 + 零 `print()` 残留（全部改用 logging）
- OpenTelemetry + Prometheus 可观测性

### 社区规范
- CODE_OF_CONDUCT.md / SECURITY.md / CONTRIBUTING.md / CHANGELOG.md
- Bug Report & Feature Request Issue 模板
- `.env.example` / `.gitattributes` / `.gitignore` / `.pre-commit-config.yaml`

### 修复
- `self_correction.py` / `graph_builder.py` — LLM `chat()` / `generate()` 返回类型不匹配
- `agents.py` — HTML 表格 `<table>` / `<td>` 标签错误 + `线` 字符残留
- `generator.py` — 缓存丢失 citation 数据
- `config.py` — `ASYNC_DATABASE_URL` regex 不匹配 `+psycopg`
- `query_optimizer.py` — `data/synonyms.json` 相对路径
- 上传路径穿越漏洞（`os.path.basename()` 净化）
- APScheduler 不关闭导致僵尸线程
- HNSW 索引参数硬编码 `m=32` → 使用 `Config.VECTOR_HNSW_M`（48）
- 3 处残留 Celery import 导致运行时崩溃

### 清理
- 删除 `webui/`（Streamlit 旧版）、`tasks.py`（Celery）、`config_example.py` 等 11 个死文件
- 删除 `utils/unstructured_loader.py`、`utils/image_processor.py` 等零引用模块
- 移除未使用的 `streamlit` import

---

## [1.0.0] — 初版

- Streamlit WebUI
- BM25 + FAISS 混合检索
- 知识图谱增强
- 多模态智能体（LangGraph + CLIP）
- 自我修正
- Celery 异步索引
- 用户反馈闭环
