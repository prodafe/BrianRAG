# BrianRAG Skills Changelog

## 2026-05-29 — v1.1 更新

三大维度全面升级，skills 中差距项已大幅缩小。

- **文档解析** (75→95): 深度文档解析引擎 + 30 种格式 + 图片 AI 描述
- **Agent 能力** (55→90+): ReAct Agent 循环 + 12 工具 + 并行执行 + 自动重试
- **前端体验** (75→90+): 暗黑模式切换 + 搜索历史 + 3 级响应式 + 骨架屏

---

## 2026-05-28 — 首次发布 v1.0

新增 3 个 BrianRAG 专用 Claude Code Skills，覆盖开发、审计、基准三大场景。

---

### `/brianrag-dev` — 开发助手

**触发条件**：编写/修改 BrianRAG 代码时自动触发

**能力**：
- 自动遵循项目架构约定（`core/`/`api/`/`utils/`/`tests/`/`frontend/`）
- 强制日志规范（`logger` 替代 `print`）
- 强制异常处理规范（禁止裸 `except:`）
- 测试文件命名约定（`tests/test_<模块>.py`）
- API 端点规范（`tags`/`summary`/Pydantic 模型）
- 前端规范（`esc()` 防 XSS、`t()` i18n、CSS 令牌）
- 提交信息规范（`feat:`/`fix:`/`docs:`/`test:`）

**使用**：
```
/brianrag-dev 帮我在 core/retriever.py 加一个稀疏向量检索方法
```

---

### `/brianrag-audit` — 代码审计

**触发条件**：用户说"检查"/"审计"/"有没有 bug"/"全面检查"

**能力**：
- 6 维度审计清单（安全/资源/错误处理/并发/前端/配置）
- 自动化扫描脚本（裸 except、静默 pass、SQL 注入、print 残留）
- 结构化审计报告（严重度/文件:行/问题/修复）
- 线程池泄漏检测
- XSS 风险评估

**使用**：
```
/brianrag-audit 全面检查一下项目有没有 bug
```

---

### `/brianrag-bench` — 性能基准

**触发条件**：用户说"测性能"/"benchmark"/"对比"/"差多少"

**能力**：
- 检索延迟 P50/P95/P99 测试（`evaluation/benchmark.py`）
- RAGAS 质量评估 Faithfulness/Relevancy/Recall
- 与 RAGFlow/Dify 的逐项对比
- 指标解读与优化建议
- 快速诊断命令（health/docs/graph/prewarm）

**使用**：
```
/brianrag-bench 测一下现在的检索延迟
/brianrag-bench 跟 RAGFlow 对比差多少
```

---

## 安装方式

```bash
# 从 BrianRAG 仓库安装
cp -r skills/brianrag-* ~/.claude/skills/
```

安装后 Claude Code 自动识别，使用 `/brianrag-dev`、`/brianrag-audit`、`/brianrag-bench` 调用。
