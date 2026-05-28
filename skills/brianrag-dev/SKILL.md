---
name: brianrag-dev
description: "BrianRAG 开发助手 — 当编写/修改 BrianRAG 代码、新增功能、修复 bug、写测试、优化性能时自动触发。Use when writing or modifying any BrianRAG code, adding features, fixing bugs, writing tests, or optimizing performance."
---

# BrianRAG 开发规范

在 BrianRAG 项目（`C:\Users\86153\PycharmProjects\PythonProject2`）中编写代码时必须遵循以下规范。

---

## 一、项目架构约定

```
core/       — 核心引擎（检索、生成、图谱、Agent、Memory）
api/        — FastAPI 端点（main.py 唯一入口）
utils/      — 工具模块（文档加载、OCR、认证、会话、数据连接器）
tests/      — 测试（pytest，文件名 test_<模块>.py）
frontend/   — 前端（index.html + admin.html + js/ + styles/）
docs/       — 文档（API.md、GUIDE.md、DEPLOY.md、README_EN.md）
evaluation/ — 评估（benchmark.py、ragas_runner.py）
```

## 二、代码规范

### 配置
- 所有配置通过 `from config import Config` 读取
- 使用 `Config.FIELD_NAME` 或 `getattr(Config, "field", default)`
- pydantic-settings 字段为 `lower_case`，自动映射 `UPPER_CASE`
- 线程安全覆写用 `with config_override(**kwargs):`

### 核心模块
- RAG Pipeline 统一入口: `core/rag_pipeline.py` → `RAGPipeline`
- 检索器: `core/retriever.py` → `HybridRetriever`
- LLM Provider: `core/llm_provider.py` → `get_llm_provider()`
- Redis: `core/redis_client.py` → `get_redis(db=N)`
- Memory: `core/memory.py` → `get_user_memory(user_id)`

### 日志
- 使用 `logging.getLogger(__name__)`
- 禁止 `print()`，全用 `logger.info/warning/error/debug`
- 异常必须记录: `logger.error(f"...: {e}", exc_info=True)`

### 异常处理
- 禁止裸 `except:`，最宽用 `except Exception:`
- 可选依赖缺失: `except ImportError:` 允许 `pass`
- API 层所有异常返回友好中文错误

### 类型注解
- 核心模块必须有 Type Hints
- 使用 `from __future__ import annotations` 延迟求值
- `list[dict]` 而非 `List[Dict]` (Python 3.10+)

## 三、测试规范

- 每个 `core/*.py` 和 `utils/*.py` 对应 `tests/test_<name>.py`
- 用 `monkeypatch` mock 外部依赖（Redis、Ollama、transformers）
- 测试类名 `Test<功能>`，方法名 `test_<场景>`
- 运行: `.venv/Scripts/python -m pytest tests/ -v`
- 目标: 每个新模块 ≥5 个测试

## 四、API 规范

- 所有端点加 `tags=["Category"]` 和 `summary="中文描述"`
- 请求体用 Pydantic `BaseModel`
- 大文件用 `UploadFile` + `FormData`
- 流式响应用 `StreamingResponse` + SSE `data: {json}\n\n`

## 五、前端规范

- HTML 模板: `frontend/index.html` (用户端) + `frontend/admin.html` (管理端)
- JS 模块: `frontend/js/app.js` + `frontend/js/i18n.js`
- CSS: `frontend/styles/main.css`
- DOM 查询: `$('#id')` / `$$('.class')`
- 用户输入: `esc()` 防 XSS
- i18n: `t('key')` 查翻译
- 设计令牌: `--ink`, `--cream`, `--gold`, `--gh`, `--gm`, `--td`

## 六、提交规范

- `feat: 功能描述`
- `fix: 修复描述`
- `docs: 文档描述`
- `test: 测试描述`
- `release: vX.Y.Z — 说明`
