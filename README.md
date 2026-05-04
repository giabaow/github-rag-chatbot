# 🤖 GitHub RAG Chatbot

> Chat with any public GitHub repository using Retrieval-Augmented Generation (RAG). Ask natural language questions and get grounded, code-aware answers — with exact file citations.

![Python](https://img.shields.io/badge/Python-3.11-blue?logo=python) ![Streamlit](https://img.shields.io/badge/UI-Streamlit-red?logo=streamlit) ![LangChain](https://img.shields.io/badge/Orchestration-LangChain-green) ![ChromaDB](https://img.shields.io/badge/VectorDB-ChromaDB-orange) ![Docker](https://img.shields.io/badge/Deploy-Docker-blue?logo=docker)

---

## ✨ Features

- **Instant repo ingestion** — clone, parse, chunk, and embed any public GitHub repo in 1–3 minutes
- **Semantic search** — finds the most relevant code snippets using sentence-level embeddings (`all-MiniLM-L6-v2`)
- **Grounded answers** — Gemini 1.5 Flash answers using only retrieved context, never hallucinating beyond the codebase
- **Source citations** — every answer shows the exact file paths it drew from
- **Language-aware chunking** — splits code at logical boundaries (functions, classes, exports) rather than arbitrary character counts
- **Persistent indexes** — ChromaDB collections survive container restarts; no re-indexing needed
- **Fully containerized** — one `docker compose up` gets you running

---

## 🏗️ Architecture

```
GitHub URL
    │
    ▼
┌─────────────┐     ┌──────────────┐     ┌───────────────────┐
│ repo_loader │────▶│   chunker    │────▶│   vector_store    │
│  clone_repo │     │  chunk_files │     │ build_vector_store│
│extract_files│     │  (per-lang   │     │  (ChromaDB +      │
└─────────────┘     │  separators) │     │  SentenceTransf.) │
                    └──────────────┘     └───────────────────┘
                                                   │
                          User question             │  similarity_search
                               │                   ▼
                    ┌──────────────────────────────────────┐
                    │            pipeline.py               │
                    │  retrieve top-k chunks → build       │
                    │  context → prompt Gemini 1.5 Flash   │
                    └──────────────────────────────────────┘
                               │
                    ┌──────────▼──────────┐
                    │      app.py         │
                    │  Streamlit chat UI  │
                    └─────────────────────┘
```

### Component breakdown

| File | Role |
|---|---|
| `repo_loader.py` | Clones repos with GitPython, walks the tree, filters by extension & file size |
| `chunker.py` | Language-aware splitting with `RecursiveCharacterTextSplitter`; prepends file paths for LLM context |
| `vector_store.py` | Embeds chunks with `all-MiniLM-L6-v2`, persists to ChromaDB |
| `pipeline.py` | Orchestrates indexing and RAG query flow via LangChain + Gemini 1.5 Flash |
| `app.py` | Streamlit chat interface with source badges and chunk expanders |
| `Dockerfile` | Multi-stage build (builder + slim runtime), non-root user, health-check |
| `docker-compose.yml` | Named volumes for repos, vectors, and model cache; 4 GB memory limit |

---

## 🚀 Quick Start

### With Docker (recommended)

```bash
# 1. Clone this repository
git clone https://github.com/your-username/github-rag-chatbot.git
cd github-rag-chatbot

# 2. Set your Google API key
echo "GOOGLE_API_KEY=your_key_here" > .env

# 3. Start the app
docker compose up --build

# 4. Open http://localhost:8501
```

Data is persisted across restarts in Docker-managed volumes — no re-indexing needed.

### Local development

```bash
# Create and activate a virtual environment
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env        # then fill in GOOGLE_API_KEY

# Run the app
streamlit run app.py
```

---

## 🔧 Configuration

| Variable | Default | Description |
|---|---|---|
| `GOOGLE_API_KEY` | *(required)* | Gemini 1.5 Flash API key |
| `GPT4ALL_MODEL_PATH` | `/app/data/models` | Where the embedding model is cached |
| `ANONYMIZED_TELEMETRY` | `False` | ChromaDB telemetry opt-out |

UI controls (sidebar):

- **Top-k slider** — number of retrieved chunks per question (3–10). Higher = more context, slower response.

---

## 🧠 How It Works

### Indexing a repository

1. **Clone** — `repo_loader.py` shallow-clones the repo (`depth=1`) and walks every file
2. **Filter** — skips binary/build directories (`node_modules`, `dist`, `.git`, etc.) and files over 50 KB
3. **Chunk** — `chunker.py` splits each file at language-appropriate boundaries (e.g. `\ndef ` for Python, `\nfunction ` for JS) with 800-character chunks and 100-character overlap
4. **Embed & store** — `vector_store.py` embeds chunks with `all-MiniLM-L6-v2` and writes them to a per-repo ChromaDB collection

### Answering a question

1. **Retrieve** — runs semantic similarity search, returning the top-k chunks
2. **Build context** — formats chunks with file paths and relevance scores
3. **Generate** — sends a strict RAG prompt to Gemini 1.5 Flash (temperature 0.2), instructing it to answer only from the provided context
4. **Display** — streams the answer to the Streamlit chat UI, with source file badges and an expandable chunk viewer

---

## 📁 Supported File Types

`.py` `.js` `.ts` `.tsx` `.jsx` `.md` `.json` `.yaml` `.yml` `.html` `.css` `.java` `.go` `.rs` `.cpp` `.c` `.h` `.rb` `.php` `.sh` `.toml` `.ini` `.cfg`

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| LLM | Gemini 1.5 Flash (via `langchain-google-genai`) |
| Embeddings | `all-MiniLM-L6-v2` (SentenceTransformers, runs locally) |
| Vector database | ChromaDB |
| Orchestration | LangChain |
| UI | Streamlit |
| Repo cloning | GitPython |
| Containerization | Docker + Docker Compose |

---

## 📦 Project Structure

```
.
├── app.py                  # Streamlit UI
├── backend/
│   └── rag/
│       ├── pipeline.py     # Indexing & RAG query orchestration
│       ├── repo_loader.py  # Clone + file extraction
│       ├── chunker.py      # Language-aware text splitting
│       └── vector_store.py # ChromaDB embedding & retrieval
├── data/
│   ├── repos/              # Cloned repositories (volume-mounted)
│   └── vectors/            # ChromaDB collections (volume-mounted)
├── Dockerfile
├── docker-compose.yml
├── requirements.txt
└── .env.example
```

---

## 🔒 Security Notes

- The Docker image runs as a **non-root user** (`appuser`, UID 1000)
- Your `GOOGLE_API_KEY` should be set via `.env` and **never committed to version control**
- Only **public** GitHub repositories are supported

---

## 📄 License

MIT