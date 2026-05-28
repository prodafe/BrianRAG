# BrianRAG Skills — AI 驱动的 RAG 开发助手

在 Claude Code 中使用 `/skill-name` 一键调用。

---

## 安装

```bash
# 克隆到 Claude Code skills 目录
git clone https://github.com/prodafe/BrianRAG.git /tmp/brianrag
cp -r /tmp/brianrag/skills/brianrag-* ~/.claude/skills/
```

或者直接复制：
```bash
cp -r skills/brianrag-* ~/.claude/skills/
```

---

## Skills 列表

| 命令 | 功能 | 触发词 |
|------|------|--------|
| `/brianrag-dev` | 开发助手 — 自动遵循项目架构、代码规范、测试规范 | 写代码、改代码、新增功能 |
| `/brianrag-audit` | 代码审计 — 全面检查 bugs、安全、性能、资源泄漏 | 检查、审计、有没有 bug |
| `/brianrag-bench` | 性能基准 — 检索延迟、RAGAS 质量、顶级项目对比 | 测性能、benchmark、对比 |

---

## 使用示例

```
/brianrag-dev   帮我给 core/retriever.py 加一个稀疏向量检索方法
/brianrag-audit 全面检查一下项目有没有 bug
/brianrag-bench 测一下现在的检索延迟，跟 RAGFlow 对比
```
