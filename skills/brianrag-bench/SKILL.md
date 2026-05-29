---
name: brianrag-bench
description: "BrianRAG 性能基准 — 评估检索延迟、答案质量、对比顶级 RAG 项目。当用户说"测一下性能"、"benchmark"、"对比一下"、"评估质量"、"跟别人比差多少"时自动触发。Use when user asks to benchmark performance, evaluate quality, or compare against other RAG projects."
---

# BrianRAG 性能基准测试

对 BrianRAG 项目（`C:\Users\86153\PycharmProjects\PythonProject2`）进行性能和质量的全面基准测试。

---

## 一、检索延迟测试

```bash
cd C:\Users\86153\PycharmProjects\PythonProject2
.venv\Scripts\python -m evaluation.benchmark
```

### 指标解读
| 指标 | 优秀 | 良好 | 需优化 |
|------|:---:|:---:|:---:|
| P50 检索延迟 | <100ms | <300ms | >500ms |
| P95 检索延迟 | <500ms | <1s | >2s |
| P99 检索延迟 | <1s | <2s | >3s |

### 优化方向
- P50 高 → 检查 pgvector HNSW 索引参数（`vector_hnsw_ef_search`）
- P95 高 → 检查 BM25 重建频率、embedding 批处理大小
- 多模态慢 → 确认 CLIP 模型已加载到 GPU

## 二、RAGAS 质量评估

```bash
cd C:\Users\86153\PycharmProjects\PythonProject2
.venv\Scripts\python -m evaluation.ragas_runner
```

### 指标解读
| 指标 | 优秀 | 良好 | 需优化 |
|------|:---:|:---:|:---:|
| Faithfulness | >0.85 | >0.70 | <0.60 |
| Answer Relevancy | >0.80 | >0.65 | <0.50 |
| Context Recall | >0.80 | >0.60 | <0.45 |

### 优化方向
- Faithfulness 低 → 检查自我修正阈值（`self_correction_score_threshold`）
- Relevancy 低 → 检查 HyDE 是否启用，查询改写质量
- Recall 低 → 检查 top_k、alpha 参数，考虑启用多查询检索

## 三、与顶级项目对比

### 对比维度
| 维度 | BrianRAG | RAGFlow | Dify | 差距 |
|------|:---:|:---:|:---:|:--:|
| RAG 检索质量 | 92 | 90 | 85 | ✅ 领先 |
| 知识图谱 | 95 | 85 | 0 | ✅ 领先 |
| 文档解析 | 95 | 95 | 85 | ✅ 已追平 |
| Agent 能力 | 90 | 90 | 95 | 🟢 接近顶级 |
| 数据源 | 20 | 20+ | 20+ | 🟢 已持平 |
| 前端体验 | 90 | 90 | 95 | 🟢 接近顶级 |
| 部署便利 | 20 | 90 | 95 | 🔴 差距大 |

> 以上评分已更新至 v2.2.2。文档解析、Agent 能力、前端体验三项在 v2.2.0 中大幅升级，已追平或接近顶级水平。

### 定级标准
- 85+: 世界级
- 70-85: 生产可用
- 55-70: 需要加强
- <55: 重点建设

## 四、快速诊断命令

```bash
# 服务健康
curl -s http://localhost:8000/api/health | python -m json.tool

# 文档统计
curl -s http://localhost:8000/api/documents | python -c "import json,sys; d=json.load(sys.stdin); print(f'Docs: {len(d.get(\"documents\",[]))}')"

# 图谱统计
curl -s "http://localhost:8000/api/graph?node_limit=0" | python -c "import json,sys; d=json.load(sys.stdin); s=d.get('stats',{}); print(f'Nodes: {s.get(\"nodes\",0)}, Edges: {s.get(\"edges\",0)}, Communities: {s.get(\"communities\",0)}')"

# 预训练缓存
curl -s http://localhost:8000/api/prewarm/status
```
