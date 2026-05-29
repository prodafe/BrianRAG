# BrianRAG User Guide

## Quick Start

1. Start services: Redis, PostgreSQL, Ollama
2. `python run.py`
3. Open http://localhost:8000

## Adding Documents

### Via UI
Click "Docs" tab → drag files or click upload zone → auto-index.

### Via API
```bash
curl -X POST http://localhost:8000/api/upload -F "files=@doc.pdf"
curl -X POST http://localhost:8000/api/index -H "Content-Type: application/json" -d '{"file_paths":["data/uploads/doc.pdf"]}'
```

### Supported Formats
PDF, Markdown, DOCX, HTML, CSV, PPTX, XLSX, TXT, XML, RTF, ODT, EPUB, Python, JSON, YAML, images (PNG/JPG/GIF/BMP/WebP), ZIP archives.

## Query Modes

| Mode | Description | Best For |
|------|-------------|----------|
| **RAG** | Standard retrieval-augmented generation | Factual QA |
| **Agentic** | ReAct agent with tool calling | Multi-step reasoning |
| **Graph** | Knowledge graph-enhanced retrieval | Relationship queries |
| **Multimodal** | CLIP vision + VLM with images | Image-inclusive answers |

## Agent Tools

BrianRAG supports 12 built-in tools:

**Core Tools**
- **calc**: Math calculations (`calc:sqrt(16)*3`)
- **time**: Date/time queries (`time:now`, `time:+3天`)
- **unit**: Unit conversion (`unit:10km->m`)

**Search & Web**
- **search**: Web search via DuckDuckGo (`search:Python async patterns`)
- **wiki**: Wikipedia lookup (`wiki:quantum computing`)
- **scrape**: Web page text extraction (`scrape:https://example.com`)

**Data & Code**
- **code**: Safe Python sandbox (`code:sorted([3,1,2])`)
- **sql**: PostgreSQL read-only query (`sql:SELECT count(*) FROM chunks`)
- **api**: HTTP API calls (`api:GET|https://api.example.com`)
- **file_read**: Read indexed documents (`file_read:config.md`)
- **json**: JSON format/field extraction

**Language**
- **translate**: Chinese↔English translation (`translate:en:Hello world`)

## Knowledge Graph

- Access via "Graph" button in chat header
- Search entities with the search box
- Double-click a node to query about that entity
- Communities view: `/api/graph/communities`

## Memory System

BrianRAG remembers user preferences and facts across sessions:
- Automatically extracts key info from conversations
- Relevant memories are injected into query context
- Manage via API: `GET /api/memory/{user_id}`

## RAG Playground

Debug your RAG pipeline:
1. Click "Play" tab
2. Adjust Top-K and Alpha sliders
3. Click "Run Trace"
4. View step-by-step timing and intermediate results

## Workflow Engine

Execute custom retrieval workflows:
```bash
curl -X POST http://localhost:8000/api/workflow/run \
  -H "Content-Type: application/json" \
  -d @workflow.json
```

Built-in templates at `/api/workflow/templates`.

## Multi-Agent Mode

Planner → Retriever → Critic pipeline:
```bash
curl -X POST http://localhost:8000/api/agent/multi \
  -H "Content-Type: application/json" \
  -d '{"question":"复杂的多步推理问题"}'
```
