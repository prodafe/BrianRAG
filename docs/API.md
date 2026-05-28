# BrianRAG API Reference

Base URL: `http://localhost:8000`

## Authentication

Optional API Key via `X-API-Key` header or `BRIAN_API_KEY` env var.

---

## Core Query

### POST /api/query
Sync query. Returns full answer with citations.

```json
{"question": "减震器设计要点", "mode": "rag"}
```

Modes: `rag`, `agentic`, `graph`, `multimodal`

### GET /api/query/stream
SSE streaming query. Same params as above.

---

## Index & Documents

### POST /api/index
Trigger document indexing.
```json
{"file_paths": ["/data/doc.md"], "incremental": true}
```

### POST /api/upload
Upload files (multipart/form-data).

### GET /api/documents
List indexed documents with hashes.

### DELETE /api/documents/{hash}
Delete document by hash.

### POST /api/index/images
Batch index images into multimodal CLIP index.

---

## Knowledge Graph

### GET /api/graph
Export graph nodes and edges. Query: `?node_limit=200`

### GET /api/graph/communities
GraphRAG community detection with LLM summaries.

---

## Agent & Workflow

### GET /api/workflow/templates
List built-in workflow templates (Basic RAG, Agent+Tools).

### POST /api/workflow/run
Execute a JSON-defined workflow DAG.

### POST /api/agent/multi
Multi-agent query: Planner → Retriever → Critic.

---

## Evaluation

### POST /api/eval
Run RAGAS evaluation.

### GET /api/eval/results
Get latest evaluation results.

---

## Health & Status

### GET /api/health
```json
{"status":"ok","services":{"redis":"ok","postgresql":"ok","ollama":"ok"},
 "models":{"llm":"qwen2.5:7b","embedding":"bge-m3:latest","vision":"qwen2.5vl:7b","reranker":"configured","multimodal":"configured"}}
```

### GET /api/ocr_status
OCR engine status (paddle/tesseract/none).

### GET /api/prewarm/status
QA prewarm cache statistics.

---

## History & Feedback

### POST /api/history/add
Record a question. Query: `?question=...`

### GET /api/history/list
List recent history.

### POST /api/feedback
Submit answer feedback.
```json
{"question":"...","answer":"...","feedback":"positive","comment":""}
```

---

## Sessions & Auth

### POST /api/session/create
Create session. Query: `?name=...`

### GET /api/session/{id}
Get session data.

---

## GitHub Sync

### GET /api/github/status
### POST /api/github/sync

---

## Playground

### POST /api/playground/query
```json
{"question":"test","top_k":5,"alpha":0.5}
```

---

## Background Tasks

### GET /api/task/{task_id}
Check async task status (indexing, etc.).
