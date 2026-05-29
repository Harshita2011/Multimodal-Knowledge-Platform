# Multimodal RAG Backend

Production-oriented PDF Retrieval-Augmented Generation backend built with FastAPI, ChromaDB, SentenceTransformers, and Gemini.

## Architecture

### Ingestion Pipeline
`PDF -> Parser -> Chunker -> Embeddings -> Chroma Upsert`

### Retrieval Pipeline
`Query -> Embed -> Chroma Search -> Threshold -> Deduplicate -> Diversify -> Reranker -> Prompt Builder -> LLM -> Citations`

### Design Principles
- Modular monolith
- Orchestrator-based workflows
- Repository abstractions
- Deterministic chunk IDs and citation traceability
- Structured telemetry + query analytics + OTel export mapping

## Quick Start

```bash
cp .env.example .env
make install
make run
```

Then open:
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`

## Development Commands

```bash
make lint
make format
make typecheck
make test
make coverage
make evaluate
```

## Testing

```bash
make test
```

Coverage report:

```bash
make coverage
```

Artifacts:
- `coverage.xml`
- `htmlcov/`

## Retrieval Evaluation

```bash
make evaluate
python scripts/generate_retrieval_report.py --output-markdown
python scripts/analyze_retrieval_thresholds.py
```

## Environment

Use `.env.example` as the source of truth. Key groups:
- LLM + embeddings
- Retrieval quality and thresholds
- Token budgets
- Retry and timeout settings
- OTel export settings

## API Endpoints

- `GET /api/v1/health`
- `POST /api/v1/documents/upload`
- `POST /api/v1/chat/query`

All endpoint schemas, examples, and error contracts are available in `/docs`.
