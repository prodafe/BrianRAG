# 安全策略

## 报告漏洞

如果你发现安全漏洞，**请不要公开提交 Issue**。

请通过以下方式私下报告：

1. 发送邮件至项目维护者
2. 在 [GitHub Security Advisories](https://github.com/prodafe/BrianRAG/security/advisories) 提交

我们将在 48 小时内确认收到报告，并在 7 天内提供修复进展。

## 已内置的安全措施

### 代码执行安全
- AST 白名单安全求值器（替代 `eval()`），仅允许数学运算符和预定义函数
- Python 代码沙箱（`tool_code`），禁止导入外部模块和调用危险函数
- Jinja2 不使用，无模板注入风险

### 路径安全
- Zip Slip 路径穿越防护（`os.path.basename()` 净化）
- 文件读取限制在 `Config.DATA_DIR` 范围内
- 上传文件哈希化文件名，防止覆盖

### 线程安全
- `config_override()` 使用 `threading.local()` + `RLock` 保护
- Redis 连接池双检锁防竞态
- 共享状态 `_shared` 字典有 `RLock` 保护

### API 安全
- 可选 API Key 鉴权（`BRIAN_API_KEY` 环境变量）
- 多租户模式 RBAC（admin/editor/viewer 三种角色）
- slowapi 速率限制（60 req/min 默认）
- CORS 可配置限制

### 本地部署

BrianRAG 设计为本地/内网运行。如果暴露到公网：

- 通过环境变量 `BRIAN_API_KEY=your-key` 启用 API Key 鉴权
- 在反向代理层（nginx/Caddy）配置 HTTPS
- 限制 CORS `allow_origins` 为具体域名
- 不要将 `.env` 文件提交到版本控制
- 不要暴露 Ollama 端口到公网

### 依赖安全

- 定期运行 `pip-audit` 检查依赖漏洞
- GitHub Dependabot 已配置自动更新

### 数据隐私

- 所有文档和索引存储在本地磁盘
- LLM 推理通过本地 Ollama 完成
- 不上传任何数据到外部服务（除非显式配置 OpenAI/Anthropic API Key）
- Memory 数据存储在本地 Redis

## 支持的版本

| 版本 | 支持状态 |
|------|---------|
| 2.1.x (master) | 积极支持 |
| 2.0.x | 安全修复 |
| < 2.0 | 不再支持 |

## 漏洞披露

发现并修复的漏洞将在 [CHANGELOG.md](CHANGELOG.md) 中记录。

已知已修复的安全问题：
- v2.1.0: 线程池泄漏（僵尸线程）、裸 except 静默吞异常、路径穿越风险、装饰器语法错误
- v2.0.0: Zip Slip 防护、AST 安全求值器替代 eval()、统一 Redis 连接池双检锁、psycopg 连接 context manager
