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

## Current Limitations

- Source files must currently be selected manually.
- AI output is advisory and may contain incorrect diagnoses.
- Issue listing uses only the first page of GitHub results.
- Filtering pull requests after fetching issues can result in fewer issues than requested.
- Source file retrieval has size and file-type restrictions.
- The local AI model requires Ollama to run on the host machine.
- Automated accuracy evaluation has not yet been implemented.

## Project Status

**Stage 2 completed — Stage 3 (RAG and semantic code search) is next.**