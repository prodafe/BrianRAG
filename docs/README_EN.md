# BrianRAG — Enterprise Knowledge Engine

[![CI](https://github.com/prodafe/BrianRAG/actions/workflows/ci.yml/badge.svg)](https://github.com/prodafe/BrianRAG/actions)
[![Version](https://img.shields.io/badge/version-2.0.0-gold)](https://github.com/prodafe/BrianRAG/releases/tag/v2.0.0)
[![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-Apache%202.0-green)](LICENSE)

A production-grade, locally-first RAG knowledge engine with hybrid retrieval, knowledge graphs, multimodal support, and four query modes.

---

## Features

### Four Query Modes
| Mode | Description |
|------|-------------|
| **RAG** | Standard retrieval-augmented generation with BM25 + vector + rerank + MMR |
| **Agentic** | LangChain agent with calculator, search, and time tools |
| **Graph** | LangGraph workflow with self-correction retry loop and knowledge graph enhancement |
| **Multimodal** | Image captioning + table extraction via vision model (qwen2.5vl:7b) |

### Retrieval Pipeline
- **Hybrid Search**: BM25 (sparse) + bge-m3 embeddings (dense) + Reciprocal Rank Fusion
- **Reranking**: bge-reranker-v2-m3 cross-encoder
- **MMR**: Maximum Marginal Relevance for diversity
- **Retrieval Gating**: Auto quality check with HyDE fallback
- **Context Expansion**: Surrounding chunk injection

### Knowledge Graph
- LLM-driven entity extraction from indexed documents
- Interactive visualization with vis-network
- Graph-enhanced retrieval with neighbor hopping

### Developer Experience
- **Interactive Playground**: Real-time RAG pipeline trace with per-step timing
- **Citation Engine**: Every answer sentence traceable to source document
- **OpenAPI Docs**: 30+ endpoints with Swagger UI at `/docs`
- **Smart Model Router**: Auto-selects model based on query complexity

### Production
- Thread-safe config with per-request overrides
- Shared Redis connection pool with leak prevention
- AST-based safe expression evaluator (no eval)
- Zip slip path traversal protection
- Configurable timeouts for all LLM/embedding calls

---

## Quick Start

### Prerequisites
- Python 3.10+
- PostgreSQL with pgvector extension
- Redis
- [Ollama](https://ollama.com) with models: `qwen2.5:7b`, `bge-m3:latest`
- Optional: `qwen2.5:1.5b` (small model), `qwen2.5:14b` (complex model), `qwen2.5vl:7b` (vision)

### Install
```bash
git clone https://github.com/prodafe/BrianRAG.git
cd BrianRAG
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e .
# Pull Ollama models
ollama pull qwen2.5:7b
ollama pull bge-m3:latest
```

### Run
```bash
# Start services (PostgreSQL, Redis, Ollama), then:
python run.py
# Open http://localhost:8000
```

### Configuration
Copy `.env.example` to `.env` and adjust:
```bash
BRIAN_LLM_MODEL=qwen2.5:7b
BRIAN_EMBEDDING_MODEL=bge-m3:latest
BRIAN_DATABASE_URL=postgresql+psycopg://postgres:postgres@localhost:5432/postgres
BRIAN_REDIS_URL=redis://localhost:6379/0
BRIAN_LLM_PROVIDER=ollama  # or openai / anthropic
```

---

## API Endpoints

Full interactive docs at `/docs` (Swagger) and `/redoc`.

| Group | Key Endpoints |
|-------|---------------|
| **Query** | `POST /api/query`, `GET /api/query/stream`, `POST /api/playground/query` |
| **Index** | `POST /api/index`, `POST /api/upload`, `GET /api/documents` |
| **Graph** | `GET /api/graph` — knowledge graph nodes & edges |
| **Health** | `GET /api/health` — services status |
| **Eval** | `POST /api/eval` — RAGAS evaluation |

---

## Architecture

```
Frontend (Three.js + GSAP + SSE chat)
    │
FastAPI (port 8000)
    ├── core/rag_pipeline.py    # Main query orchestrator
    ├── core/retriever.py       # Hybrid BM25 + vector search
    ├── core/reranker.py        # Cross-encoder reranker
    ├── core/generator.py       # LLM answer generation
    ├── core/graph_builder.py   # Knowledge graph construction
    ├── core/graph_workflow.py  # LangGraph self-correcting workflow
    ├── core/agents.py          # Multimodal agent (vision + tables)
    ├── core/model_router.py    # Smart model selection
    └── core/llm_provider.py    # Ollama/OpenAI/Anthropic abstraction
    │
    ├── PostgreSQL + pgvector   # Vector store (HNSW index)
    ├── Redis                   # Cache (4 DBs) + sessions
    ├── FAISS                   # In-memory vector index (fallback)
    └── Ollama                  # Local LLM inference
```

---

## Development

```bash
pip install -e ".[dev]"
pytest tests/ -v          # 46 tests
ruff check .              # lint
mypy core/                # type check
```

---

## License

Apache 2.0 — see [LICENSE](LICENSE).

## Citation

```bibtex
@software{brianrag2025,
  author = {Brian},
  title = {BrianRAG: Enterprise Knowledge Engine},
  year = {2025},
  version = {2.0.0},
  url = {https://github.com/prodafe/BrianRAG}
}
```

[中文文档](../readme.md) | [Changelog](../CHANGELOG.md)
