# 安全策略

## 报告漏洞

如果你发现安全漏洞，**请不要公开提交 Issue**。

请通过以下方式私下报告：

1. 发送邮件至项目维护者
2. 在 [GitHub Security Advisories](https://github.com/your-org/brianrag/security/advisories) 提交

我们将在 48 小时内确认收到报告，并在 7 天内提供修复进展。

## 已知安全考量

### 本地部署

BrianRAG 设计为本地/内网运行。如果暴露到公网：

- 通过环境变量 `BRIAN_API_KEY=your-key` 启用 API Key 鉴权
- 在反向代理层（nginx/Caddy）配置 HTTPS
- 限制 CORS `allow_origins` 为具体域名
- 不要将 `.env` 文件提交到版本控制

### 依赖安全

- 定期运行 `pip-audit` 检查依赖漏洞
- GitHub Dependabot 已配置自动更新

### 数据隐私

- 所有文档和索引存储在本地磁盘
- LLM 推理通过本地 Ollama 完成
- 不上传任何数据到外部服务（除非配置 OpenAI/Anthropic）

## 支持的版本

| 版本 | 支持状态 |
|------|---------|
| 1.x (main) | 积极支持 |

## 漏洞披露

发现并修复的漏洞将在 CHANGELOG.md 中记录。
