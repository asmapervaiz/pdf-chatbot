# PDF Chatbot

A Python-based chatbot that answers user questions using content extracted from uploaded PDF documents. Built with FastAPI, NLP embeddings, and optional LLM integration for the **AppLab AI/ML Engineer** assignment.

---

## Features

- **Document upload API** — Upload PDFs; text is extracted, chunked, and indexed.
- **Chatbot API** — Ask questions and get answers grounded in your documents (RAG).
- **Streamlit UI** — Upload PDFs, chat, and clear index from a Python UI.
- **Docker** — Single container run with all dependencies.

---

## Setup

### Prerequisites

- Python 3.11+
- (Optional) Docker and Docker Compose

### Local development

1. **Clone and enter the project**
   ```bash
   git clone <repo-url>
   cd pdf-chatbot
   ```

2. **Create a virtual environment and install dependencies**
   ```bash
   python -m venv .venv
   .venv\Scripts\activate   # Windows
   # source .venv/bin/activate   # Linux/macOS
   pip install -r requirements.txt
   ```

3. **Optional: copy environment file**
   ```bash
   copy .env.example .env   # Windows
   # cp .env.example .env   # Linux/macOS
   ```
   Set `OPENAI_API_KEY` in `.env` to use **OpenAI text-embedding-3-small** for embeddings and **gpt-3.5-turbo** for answers. 

4. **Run backend + Streamlit UI together** (single command)
   ```bash
   python -m app.main
   ```
   This starts the API at [http://localhost:8000](http://localhost:8000) and the Streamlit UI at [http://localhost:8501](http://localhost:8501). Open **http://localhost:8501** to upload PDFs and chat. API docs: [http://localhost:8000/docs](http://localhost:8000/docs).

   To run backend and UI separately (two terminals):
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   streamlit run streamlit_app.py
   ```
   Set `API_URL` if the UI should use a different API URL (e.g. `set API_URL=http://localhost:8000` on Windows).

### Docker

```bash
docker-compose up --build
```

Then open [http://localhost:8000](http://localhost:8000). Data is persisted in `./uploads` and `./data`.

---

## API Documentation

### Base URL

- Local: `http://localhost:8000`
- Interactive docs: `GET http://localhost:8000/docs`

### Endpoints

#### Health

- **GET** `/health`  
  - Response: `{ "status": "ok", "message": "PDF Chatbot API is running" }`

#### Document upload

- **POST** `/documents/upload`  
  - **Content-Type:** `multipart/form-data`  
  - **Body:** `file` — PDF file  
  - **Response:**  
    ```json
    {
      "message": "Document uploaded and processed successfully",
      "filename": "example.pdf",
      "pages_processed": 5,
      "chunks_indexed": 42
    }
    ```
  - **Errors:** 400 (invalid type/size), 422 (unprocessable PDF)

#### Chat

- **POST** `/chat/ask`  
  - **Content-Type:** `application/json`  
  - **Body:**  
    ```json
    { "question": "What is the main topic of the document?" }
    ```
  - **Response:**  
    ```json
    {
      "answer": "The document discusses...",
      "sources": ["Excerpt from chunk 1...", "Excerpt from chunk 2..."]
    }
    ```

---

## Project structure

```
pdf-chatbot/
├── app/
│   ├── __init__.py
│   ├── main.py           # FastAPI app, routes, static serve
│   ├── config.py         # Settings (env, paths, model names)
│   ├── api/
│   │   ├── documents.py  # POST /documents/upload
│   │   └── chat.py       # POST /chat/ask
│   ├── models/
│   │   └── schemas.py    # Pydantic request/response models
│   └── services/
│       ├── pdf_service.py        # PDF text extraction & chunking
│       ├── embeddings_service.py # Sentence embeddings + ChromaDB
│       └── chat_service.py       # RAG: retrieve + generate answer
├── static/               # Frontend (HTML, CSS, JS)
├── uploads/              # Uploaded PDFs (created at runtime)
├── data/                 # ChromaDB vector store (created at runtime)
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── README.md
```

---

## Design and architecture

- **Document pipeline:** PDF → PyMuPDF text extraction → sentence-aware chunking → embeddings (Sentence Transformers) → ChromaDB.
- **Chat pipeline:** User question → embed → similarity search in ChromaDB → top-k chunks as context → LLM (OpenAI if key set, else HuggingFace FLAN-T5) → answer + source excerpts.
- **NLP/AI choices:**  
  - Embeddings: `text-embedding-3-small` for fast, good-quality semantic search.  
  - Vector store: ChromaDB for persistence and simple API.  
  - Generator: Configurable (OpenAI) for flexibility and offline use.
