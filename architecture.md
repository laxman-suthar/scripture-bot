# Scripture Bot — Architecture Note

## Overview

Scripture Bot is a Retrieval-Augmented Generation (RAG) chatbot grounded entirely in the Holy Bible. It answers questions using only verified scripture, detects hallucinated/fake verses, adapts to Catholic / Protestant / Orthodox perspectives, and optionally generates biblical illustrations. It runs fully containerised with Docker Compose.

---

## System Architecture

```
User (Browser)
      │
      ▼
┌─────────────────────────────────────────────────┐
│              Django 5  (Port 8000)              │
│                                                 │
│  ┌──────────────┐    ┌──────────────────────┐  │
│  │  chat/views  │───▶│  Moderation Layer    │  │
│  │  POST /api/  │    │  (keyword + regex)   │  │
│  │  chat/       │    └──────────┬───────────┘  │
│  └──────┬───────┘               │ safe?        │
│         │                       ▼              │
│         │            ┌──────────────────────┐  │
│         │            │   RAG Pipeline       │  │
│         │            │  ┌────────────────┐  │  │
│         │            │  │  Embedder      │  │  │
│         │            │  │ (Configurable: │  │  │
│         │            │  │  embedding-001)│  │  │
│         │            │  └───────┬────────┘  │  │
│         │            │          │ query vec  │  │
│         │            │  ┌───────▼────────┐  │  │
│         │            │  │  Retriever     │  │  │
│         │            │  │ pgvector       │  │  │
│         │            │  │ cosine search  │  │  │
│         │            │  │  top-k=5       │  │  │
│         │            │  └───────┬────────┘  │  │
│         │            │          │ verses     │  │
│         │            │  ┌───────▼────────┐  │  │
│         │            │  │  Gemini LLM    │  │  │
│         │            │  │ (Configurable: │  │  │
│         │            │  │  1.5-flash)    │  │  │
│         │            │  └───────┬────────┘  │  │
│         │            └──────────┼───────────┘  │
│         │                       │              │
│         │◀──────────────────────┘              │
│  Session Memory (DB-backed, 24h, last 10 msgs) │
└─────────────────────────────────────────────────┘
                │
                ▼
┌─────────────────────────────────────────────────┐
│     PostgreSQL 16 + pgvector  (Port 5433)       │
│                                                 │
│   BibleVerse table                              │
│   ┌─────────┬─────────┬───────┬──────────────┐ │
│   │  book   │ chapter │ verse │ embedding[]  │ │
│   │  (idx)  │  (idx)  │       │  768 floats  │ │
│   └─────────┴─────────┴───────┴──────────────┘ │
│   IVFFlat index — vector_cosine_ops, lists=100  │
└─────────────────────────────────────────────────┘
```

---

## Key Components

| Component | File | Responsibility |
|---|---|---|
| **Chat API** | `chat/views.py` | Intent routing (Q&A / image / moderated), session memory |
| **RAG Pipeline** | `rag/pipeline.py` | Prompt construction, denomination context, Gemini call, summary memory |
| **Retriever** | `rag/retriever.py` | pgvector cosine search + direct verse lookup + book alias normalisation |
| **Embedder** | `rag/embedder.py` | Configurable embedding model with key rotation and auto-fallback |
| **Moderator** | `moderation/moderator.py` | Keyword + regex guard against hate speech, violence, scripture fabrication |
| **Image Gen** | `image_gen/` | Biblical illustration generation on request |
| **Data Model** | `chat/models.py` | `BibleVerse` (book, chapter, verse, text, embedding) with IVFFlat index |

---

## Request Flow

```
1. POST /api/chat/ { "message": "..." }
2. Moderation check  →  block or pass
3. Intent detection  →  image request OR text Q&A
4. [Text path]
   a. Detect denomination (catholic / protestant / orthodox / general)
   b. Detect explicit verse reference (regex) → direct DB lookup
   c. Semantic search via pgvector (top-5 cosine similarity)
   d. Merge direct + semantic results, build context block
   e. Inject denomination prompt + rolling conversation summary
   f. Call configurable Gemini LLM with strict "cite only what you have" prompt
   g. Extract cited references from response (regex)
   h. Update session memory (last 10 msgs) + progressive summary
5. Return { response, type, verses_cited, denomination }
```

---

## Infrastructure

| Service | Image / Tech | Notes |
|---|---|---|
| Web | `python:3.12-slim` + Gunicorn | Django 5, DRF, LangChain |
| DB | `pgvector/pgvector:pg16` | Port 5433 (host), pgvector extension |
| Sessions | PostgreSQL-backed | 24 h TTL, last-10-message window |
| API Keys | Multi-key rotation | Comma-separated `GEMINI_API_KEYS`, auto-cycle on quota errors |
| Config | `.env` variables | Fully configurable model names (`GEMINI_LLM_MODEL`, `GEMINI_EMBEDDING_MODEL`) |

---

## Evaluation Coverage

| Suite | # Cases | What it tests |
|---|---|---|
| `fake_verses.json` | 5 | Hallucination rejection (out-of-range chapters/verses) |
| `real_verses.json` | 5 | Correct citation of canonical verses |
| `adversarial.json` | 10 | Prompt injection, hate speech, scripture fabrication |
| `denomination.json` | 4 | Catholic / Protestant / Orthodox awareness |
| `edge_cases.json` | 8 | Ambiguous refs, multi-verse, off-topic, short prompts |

Run all suites: `python eval/run_eval.py` (requires running server)

---

*Stack: Django 5 · PostgreSQL 16 · pgvector · Configurable Gemini Models (decouple) · LangChain · Docker Compose*
