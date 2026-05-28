# BrianRAG Deployment Guide

## Prerequisites

- Python 3.10+, PostgreSQL 14+ with pgvector, Redis 5+, Ollama

## Manual Setup

```bash
git clone https://github.com/prodafe/BrianRAG.git
cd BrianRAG
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -e ".[dev]"

# Pull models
ollama pull qwen2.5:7b
ollama pull bge-m3:latest
ollama pull qwen2.5vl:7b  # for multimodal

# Init database
psql -U postgres -c "CREATE EXTENSION IF NOT EXISTS vector"

# Start
python run.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `BRIAN_LLM_PROVIDER` | ollama | ollama/openai/anthropic |
| `BRIAN_LLM_MODEL` | qwen2.5:7b | Model name |
| `BRIAN_DATABASE_URL` | postgresql+psycopg://... | PG connection |
| `BRIAN_REDIS_URL` | redis://localhost:6379/0 | Redis connection |
| `BRIAN_ENABLE_RERANK` | true | Enable reranker |
| `BRIAN_ENABLE_MULTIMODAL` | true | Enable CLIP/vision |
| `OPENAI_API_KEY` | - | Auto-detected for OpenAI |
| `ANTHROPIC_API_KEY` | - | Auto-detected for Anthropic |

## Data Source Setup

### GitHub
```env
BRIAN_GITHUB_REPO_URL=https://github.com/user/repo
BRIAN_GITHUB_TOKEN=ghp_xxx
```

### Notion
```env
NOTION_API_KEY=ntn_xxx
```

### S3/MinIO
```env
S3_ENDPOINT=https://s3.amazonaws.com
S3_BUCKET=my-bucket
S3_ACCESS_KEY=xxx
S3_SECRET_KEY=xxx
```

### Confluence
```env
CONFLUENCE_URL=https://xxx.atlassian.net/wiki
CONFLUENCE_EMAIL=user@example.com
CONFLUENCE_TOKEN=xxx
```

### WebDAV
```env
WEBDAV_URL=https://cloud.example.com/remote.php/dav
WEBDAV_USER=user
WEBDAV_PASS=pass
```

### Google Drive
Place `service-account.json` in project root.
