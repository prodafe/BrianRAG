# 贡献指南

欢迎为 BrianRAG 做贡献！无论是报告 bug、建议新功能还是提交代码，都非常感谢。

## 开发环境

```bash
git clone https://github.com/prodafe/BrianRAG.git
cd BrianRAG
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
```

依赖服务：PostgreSQL 14+ (pgvector)、Redis 5+、Ollama

## 项目架构

```
core/       — 核心引擎（rag_pipeline / retriever / generator / graph / agent / memory / workflow）
api/        — FastAPI 端点（main.py 唯一入口，37 个端点）
utils/      — 工具模块（document_loader / ocr / auth / session / data_connectors / layout_analyzer）
tests/      — 测试（pytest，19 个测试文件，184 tests）
frontend/   — 前端（index.html / admin.html / js/ / styles/）
docs/       — 文档（API.md / GUIDE.md / DEPLOY.md）
evaluation/ — 评估（benchmark.py / ragas_runner.py）
skills/     — Claude Code Skills（brianrag-dev / brianrag-audit / brianrag-bench）
```

## 代码规范

- Python 3.10+
- 类型注解：核心模块需标注参数和返回值类型
- 命名：`snake_case` 变量/函数，`PascalCase` 类名
- 日志：使用 `logging.getLogger(__name__)`，禁止 `print()`
- 异常：禁止裸 `except:`，API 层返回友好中文错误
- 配置：通过 `from config import Config` 读取

运行检查：

```bash
ruff check .           # lint
pytest tests/ -v       # 测试
```

## 测试规范

- 每个 `core/*.py` 和 `utils/*.py` 对应 `tests/test_<name>.py`
- 用 `monkeypatch` mock 外部依赖
- 新增模块至少 5 个测试
- 目标：184 tests 全部通过

```bash
pytest tests/ -q                 # 全部（快速）
pytest tests/test_retriever.py   # 单个模块
```

## 提交规范

- `feat: 新增功能描述`
- `fix: 修复问题描述`
- `docs: 文档更新`
- `test: 测试相关`
- `release: vX.Y.Z — 说明`

## Pull Request 流程

1. Fork 仓库并创建功能分支
2. 编写代码 + 测试
3. 运行 `ruff check . && pytest tests/`
4. 提交 PR，描述改动内容和原因
5. CI 自动运行 lint + typecheck + test，全部通过后才能合并

## Claude Code Skills

项目内置 3 个 Skills，安装后自动触发：

```bash
cp -r skills/brianrag-* ~/.claude/skills/
```

| 命令 | 功能 |
|------|------|
| `/brianrag-dev` | 开发助手 — 自动遵循项目规范 |
| `/brianrag-audit` | 代码审计 — 全面检查 bugs/安全 |
| `/brianrag-bench` | 性能基准 — 检索延迟/质量评估 |

详见 [SKILLS.md](SKILLS.md)
