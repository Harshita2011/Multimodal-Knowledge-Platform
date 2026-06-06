# Multimodal RAG Backend

Production-oriented PDF Retrieval-Augmented Generation backend built with FastAPI, ChromaDB, SentenceTransformers, and Gemini.

## Architecture

### Ingestion Pipeline
`PDF -> Parser -> Chunker -> Embeddings -> Chroma Vector Upsert + Postgres Lexical Chunks & Entities Index`

### Retrieval Pipeline (Enterprise RAG V1.1)
`Query -> Intent Routing -> Hybrid Channels (Chroma Dense Vector + Postgres BM25 + Postgres Entities) -> RRF Fusion -> Reranker -> Coherence Filter & Dynamic Chunk Preservation -> Context Compressor -> Prompt Builder -> LLM -> Citations`

### Design Principles
- **Modular Monolith**: Clean domain boundaries with separation of ingestion, retrieval, database, and API logic.
- **Orchestrator-Based Workflows**: RAG retrieval and generation orchestrated dynamically by intent and query strategy.
- **Repository Abstractions**: Clean separation of PostgreSQL for relational & lexical data, and ChromaDB for vector data.
- **Deterministic Chunk IDs & Citation Traceability**: End-to-end trace from source document pages to generated answers.
- **Structured Telemetry & Query Analytics**: Out-of-the-box OpenTelemetry export mapping, query metrics, and retrieval traces.

---

## Core Features & Upgrades

### 1. Hybrid Retrieval Pipeline & Query Routing
- **Intent Routing & Query Scoping**: Classifies queries into retrieval profiles (e.g. `FAST`, `BALANCED`, `DEEP`) and scopes retrieval to active workspace/ownership context.
- **Hybrid Channels**: Executes dense vector search (ChromaDB), lexical keyword search (PostgreSQL FTS/BM25 & Trigrams), and entity matching (PostgreSQL Entity Dictionary) in parallel.
- **RRF Fusion**: Fuses multiple retrieval channels using reciprocal rank fusion (RRF) with configurable constants. Supports deterministic tie-breaking by disabling RRF where required.
- **Cross-Encoder Reranking**: Re-evaluates chunk relevance dynamically to bubble up the most relevant content.

### 2. Context Coherence & Prompt Engineering
- **Dynamic Chunk Preservation**: Keeps a minimum of:
  - `5 chunks` for detailed explanation queries (`DETAILED_EXPLANATION` mode)
  - `3 chunks` for general explanation or summary queries (`SUMMARY` or `EXPLANATION` mode)
  This replaces static ratios to guarantee sufficient context.
- **Chronological Chunk Sorting**: Prior to generating the prompt, retrieved snippets are sorted chronologically by their sequence (page number and chunk sequence) within the document. This avoids logical jumps in the context.
- **Direct System Prompts**: Instructs the LLM to output precise answers directly without conversational prefaces (e.g. "Sure! Here is the answer...").

### 3. Resilient Database Layer
- **Dynamic Database Engines**: Dynamically recreates the database engine and sessionmaker when the running asyncio event loop changes, preventing `asyncpg` "Event loop is closed" errors in testing environments.

### 4. Corpus Auditing & Repairs
The auditing and repairing processes are separated to enforce read-only audits and explicit repair controls:
- **Read-Only Audit (`scripts/audit_corpus.py`)**: Runs checks on document status, chunk-to-vector count match, missing embeddings, and ownership metadata. Creates detailed JSON/Markdown reports under `reports/`.
- **Explicit Repair (`scripts/repair_corpus.py`)**: Backfills missing user/workspace ownership metadata across both PostgreSQL tables (`chunks` metadata JSON) and ChromaDB collections, and reindexes stale documents.

---

## Quick Start

### Installation
```bash
cp .env.example .env
make install
make run
```

Then open:
- API docs: `http://127.0.0.1:8000/docs`
- Health: `http://127.0.0.1:8000/api/v1/health`

### Windows Full-Stack Development
From PowerShell:
```powershell
# Run backend + frontend
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1

# Restart backend/frontend processes
powershell -ExecutionPolicy Bypass -File scripts/dev.ps1 -Restart

# Inspect active preview ports
powershell -ExecutionPolicy Bypass -File scripts/ports.ps1
```

---

## Development Commands

```bash
make lint          # Lint checks (Ruff)
make format        # Format code (Ruff)
make typecheck     # Type checking (Mypy)
make test          # Run test suite
make coverage      # Generate coverage reports
make evaluate      # Evaluate retrieval metrics
```

### Retrieval Evaluation
Validate retrieval quality across multiple document types (e.g., resumes, slide decks, papers, DOCX files):
```bash
make evaluate
python scripts/generate_retrieval_report.py --output-markdown
python scripts/analyze_retrieval_thresholds.py
```

### Corpus Auditing & Repairs
```bash
# Read-Only Audit (creates reports/corpus_audit.json & reports/corpus_audit.md)
python scripts/audit_corpus.py

# Explicit Repairs (backfills database metadata and reindexes stale files)
python scripts/repair_corpus.py
```

---

## Environment

Use `.env.example` as the source of truth. Key configurations:
- LLM models and credentials
- Vector store configuration
- Retrieval thresholds and strategies
- Context budgets and token limits
- OpenTelemetry settings

---

## API Endpoints

- `GET /api/v1/health`
- `POST /api/v1/documents/upload`
- `POST /api/v1/chat/query`

All endpoint schemas, example payloads, and error codes are interactive at `/docs`.
