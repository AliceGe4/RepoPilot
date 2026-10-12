# RepoPilot — AI-Powered GitHub Issue Analyzer

RepoPilot is an AI-powered developer tool designed to analyze GitHub issues, inspect repository source code, and help developers identify potential bugs and debugging solutions.

The project uses **Python, FastAPI, and locally hosted AI models through Ollama**, allowing AI-assisted code analysis without paid API services.

## Tech Stack

- **Python** — Backend development
- **FastAPI** — REST API framework
- **HTTPX** — Asynchronous GitHub API communication
- **GitHub REST API** — Repository, issue, and source code retrieval
- **Ollama** — Local AI model execution
- **Qwen2.5-Coder 3B** — AI-powered code analysis
- **Pydantic** — Request validation and structured AI responses
- **Git** — Version control

## Development Progress

### Stage 1 — GitHub Integration 

Implemented a FastAPI backend that communicates with the GitHub REST API.

**Features:**
- Retrieve repository information.
- Retrieve open, closed, and all GitHub issues.
- Retrieve individual issues by number.
- Discover repository source files recursively.
- Filter source files by extension.
- Retrieve and decode source code.
- Handle common GitHub API errors.

### Stage 2 — Local AI Integration 

Integrated a locally hosted coding-focused language model using Ollama.

**Features:**
- Analyze GitHub issues using Qwen2.5-Coder 3B.
- Include up to three manually selected source files in the analysis.
- Generate structured JSON containing:
  - Issue summary
  - Possible cause
  - Suggested debugging steps
  - Confidence level
  - Analysis limitations
- Validate AI responses using Pydantic.
- Track input and output token usage.
- Handle common AI connection and response errors.

**Testing:**

Successfully tested the AI integration against Flask issue #4170 and RepoPilot issue #1.

The model correctly recognized pagination and filtering as possible causes of RepoPilot's issue-count bug, although it did not identify the exact fix.

These tests confirm the end-to-end integration works. More extensive accuracy evaluation is planned.

### Stage 3 — Retrieval-Augmented Generation (Planned)

The next stage will enable RepoPilot to automatically find relevant source code instead of requiring users to select files manually.

**Planned features:**
- Retrieve and process repository source files.
- Split source code into smaller chunks.
- Generate embeddings using a local model.
- Store embeddings in a vector database.
- Implement semantic code search.
- Automatically provide relevant code to the AI analyzer.
- Evaluate retrieval accuracy against known issues.

### Stage 4 — Frontend (Planned)

Build a React and TypeScript frontend for interacting with RepoPilot.

### Stage 5 — Testing and Deployment (Planned)

Implement automated testing, improve AI evaluation, and prepare the application for deployment.

## Installation and Setup

### Prerequisites

- Python 3.11 or newer
- Git
- Ollama installed locally

### 1. Clone the repository

`git clone https://github.com/AliceGe4/RepoPilot.git`

`cd RepoPilot`

### 2. Create a virtual environment

`python -m venv .venv`

Activate it on Windows PowerShell:

`.\.venv\Scripts\Activate.ps1`

### 3. Install dependencies

`python -m pip install -r requirements.txt`

### 4. Set up Ollama

Install Ollama from https://ollama.com/download.

Download the AI model:

`ollama pull qwen2.5-coder:3b`

Ollama must be running locally when performing AI analysis.

### 5. Configure environment variables

Create a `.env` file in the project's root directory:

`GITHUB_TOKEN=`

`OLLAMA_MODEL=qwen2.5-coder:3b`

The GitHub token is optional for public repositories, subject to GitHub API rate limits.

### 6. Run the backend

`python -m uvicorn main:app --reload`

Open the API documentation:

http://127.0.0.1:8000/docs

## API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/api/repos/{owner}/{repo}` | Repository information |
| GET | `/api/repos/{owner}/{repo}/issues` | List and filter issues |
| GET | `/api/repos/{owner}/{repo}/issues/{number}` | Retrieve one issue |
| GET | `/api/repos/{owner}/{repo}/files` | List source files |
| GET | `/api/repos/{owner}/{repo}/files/content` | Read a source file |
| POST | `/api/repos/{owner}/{repo}/analyze` | Analyze an issue using local AI |

## Example AI Analysis

Send a POST request to:

`/api/repos/AliceGe4/RepoPilot/analyze`

Request body:

`{"issue_number": 1, "file_paths": ["main.py"]}`

RepoPilot retrieves the issue and source file from GitHub and sends them to the local AI model.

The response includes a summary, possible cause, suggested debugging steps, confidence, limitations, and token usage.

## Stage 3 — Retrieval-Augmented Generation (RAG)

### Stage 3A — Semantic Code Search (In Progress)

Implemented the foundation of a local semantic search system that allows RepoPilot to find source code relevant to a GitHub issue.

Instead of relying on exact keyword matches, the system uses vector embeddings to identify code sections that may be semantically related to a problem.

**Implemented functionality:**
- Discover and retrieve repository source files through the GitHub REST API.
- Split source files into smaller, overlapping chunks.
- Preserve source filenames and line numbers for each chunk.
- Generate vector embeddings locally using Ollama and `nomic-embed-text`.
- Store embeddings and source-code metadata in a local JSON index.
- Calculate cosine similarity between a search query and indexed code chunks.
- Rank and return the most relevant source-code sections.
- Cache indexes locally to avoid regenerating embeddings for every search.

### Technologies

- Python and FastAPI
- Ollama
- nomic-embed-text
- GitHub REST API
- Vector embeddings
- Cosine similarity
- JSON-based local storage

### How Semantic Search Works

1. Retrieve eligible source files from a GitHub repository.
2. Divide the source code into overlapping chunks.
3. Generate an embedding vector for each chunk.
4. Store the vectors with their original code and file metadata.
5. Convert a user's search query into an embedding.
6. Compare the query embedding against stored embeddings using cosine similarity.
7. Return the highest-ranking code chunks.

### New API Endpoints

**POST `/api/repos/{owner}/{repo}/index`**

Downloads eligible repository files, generates embeddings, and saves the searchable index locally.

**GET `/api/repos/{owner}/{repo}/search`**

Searches an existing repository index using a natural-language query.

Parameters:
- `owner` — GitHub repository owner.
- `repo` — Repository name.
- `query` — Natural-language description of the code to find.
- `top_k` — Maximum number of matching chunks to return (1–5).

### Example Usage

First, build the repository index:

`POST /api/repos/AliceGe4/RepoPilot/index`

Then search for relevant code:

`GET /api/repos/AliceGe4/RepoPilot/search?query=GitHub%20issue%20pagination&top_k=3`

The search response contains source filenames, line numbers, similarity scores, and matching code.

### Local Setup

Download the embedding model:

`ollama pull nomic-embed-text`

Add this configuration to your `.env` file:

`EMBEDDING_MODEL=nomic-embed-text`

Make sure Ollama is running before building or searching an index.

### Current Limitations

- Indexing is limited to 30 eligible source files and 120 code chunks.
- Files larger than 12 KB are skipped.
- Chunking is based on lines and character limits rather than code syntax.
- The current vector index uses local JSON storage rather than a dedicated vector database.
- Repository indexes must be rebuilt after source code changes.
- Semantic similarity does not guarantee that retrieved code is relevant.
- Automatic retrieval has not yet been connected to the AI analysis endpoint.

### Stage 3B — Automatic AI Context Retrieval (Next)

Planned improvements:

- Automatically retrieve code related to a selected GitHub issue.
- Supply the highest-ranking source-code chunks to Qwen2.5-Coder.
- Include source-file references and line numbers in AI analyses.
- Compare issue analyses with and without retrieved code.
- Evaluate retrieval accuracy using known GitHub bugs.
- Investigate persistent vector storage using PostgreSQL and pgvector.