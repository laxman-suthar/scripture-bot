# Scripture Bot 📖✝️

An AI-powered Christianity chatbot that provides scripture-grounded answers using RAG (Retrieval-Augmented Generation), verse verification, denomination-aware responses, and Christian image generation.

![Python](https://img.shields.io/badge/Python-3.11-blue)
![Django](https://img.shields.io/badge/Django-5.2-green)
![Docker](https://img.shields.io/badge/Docker-Compose-blue)
![LangChain](https://img.shields.io/badge/LangChain-RAG-orange)

## Features

- 🔍 **Bible Q&A** — Ask any question and get answers grounded in real KJV Bible verses with citations
- ✅ **Verse Verification** — Check if a Bible verse is real or fake
- ⛪ **Denomination Support** — Catholic, Protestant, and Orthodox-aware responses
- 🎨 **Image Generation** — Generate Christian-themed artwork using AI
- 🛡️ **Content Safety** — Built-in moderation blocks harmful and manipulative prompts
- 💬 **Conversation Memory** — Session-based chat history for contextual follow-ups
- 🐳 **Dockerized** — One command to start everything

## Quick Start

### Prerequisites
- Docker & Docker Compose installed
- A Google Gemini API key ([get one free](https://makersuite.google.com/app/apikey))

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/scripture-bot.git
cd scripture-bot
```

### 2. Set up environment
```bash
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY
```

### 3. Start the application
```bash
docker compose up --build
```

### 4. Load Bible data
```bash
# Load all ~31,000 KJV verses (takes ~15-20 minutes due to embedding API rate limits)
docker compose exec web python manage.py load_bible

# Or load a smaller test set first
docker compose exec web python manage.py load_bible --limit 500
```

### 5. Open the chat
Visit **http://localhost:8000** in your browser.

## API Endpoints

| Method | URL | Purpose |
|---|---|---|
| `GET` | `/` | Chat UI page |
| `POST` | `/api/chat/` | Send message, get AI response |
| `POST` | `/api/image/` | Generate Christian-themed image |

### Chat API Example
```bash
curl -X POST http://localhost:8000/api/chat/ \
  -H "Content-Type: application/json" \
  -d '{"message": "What does John 3:16 say?"}'
```

### Image API Example
```bash
curl -X POST http://localhost:8000/api/image/ \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Jesus walking on water at sunset"}'
```

## Project Structure

```
scripture-bot/
├── scripture_bot/          # Django project settings
├── chat/                   # Main chat app (models, views, templates)
├── rag/                    # RAG pipeline (embedder, retriever, pipeline)
├── moderation/             # Content safety layer
├── image_gen/              # Pollinations.ai image generation
├── eval/                   # Evaluation dataset & test runner
├── docs/                   # Architecture documentation
├── Dockerfile
└── docker-compose.yml
```

## Evaluation

Run the automated evaluation suite against the live API:

```bash
# Make sure the server is running first
python eval/run_eval.py
```

This tests:
- ❌ 5 fake verses → should be rejected
- ✅ 5 real verses → should be cited correctly
- 🛡️ 3 adversarial prompts → should be blocked
- ⛪ 2 denomination questions → should be denomination-aware

## Architecture

See [docs/architecture.md](docs/architecture.md) for detailed technical decisions including:
- Why RAG instead of pure LLM
- Why pgvector for vector storage
- How verse verification works
- How the safety layer works
- Trade-offs and limitations

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.2 + Django REST Framework |
| AI / LLM | Google Gemini via LangChain |
| Embeddings | Gemini embedding-001 |
| Vector DB | pgvector (PostgreSQL 16) |
| Image Gen | Pollinations.ai (free, no key) |
| Memory | Django Sessions |
| Safety | Keyword filter + Gemini system prompt |
| Frontend | Django Templates + Vanilla JS |
| Deployment | Docker Compose |

## License

MIT
