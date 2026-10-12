# RepoPilot: AI-Powered GitHub Issue Analyzer

RepoPilot is a backend application designed to help developers investigate GitHub issues using AI and repository source code.

The goal is to analyze bug reports, identify potentially relevant source files, and eventually suggest possible fixes using large language models.

## Tech Stack

- **Python**
- **FastAPI** — REST API backend
- **HTTPX** — Asynchronous GitHub API requests
- **GitHub REST API** — Repository and issue information
- **Uvicorn** — Local development server

## Development Progress

### Stage 1 GitHub Integration - Completed

Implemented a FastAPI backend that communicates with the GitHub REST API.

**Completed features:**
- Retrieve GitHub repository information.
- Retrieve open, closed, or all issues.
- Retrieve a specific issue by its number.
- List repository source files recursively.
- Filter source files by extension.
- Read source code file contents.
- Handle common GitHub API errors.
- Ensured local website is able to host and handle the data.

**Current limitations:**
- Issues are retrieved from the first page only.
- File listings return a maximum of 200 matching files.
- Reading files is limited to small UTF-8 text files.
- Recursive file listings may be incomplete for very large repositories.

### Stage 2 — AI Integration (Next)

Planned features:
- Connect to an LLM API.
- Analyze an issue's title and description.
- Provide source code as context.
- Return a structured analysis of possible bugs.
- Explore retrieval-augmented generation (RAG) for larger repositories.

## Running Locally

1. Clone this repository.
2. Create a Python virtual environment:

   `python -m venv .venv`

3. Activate the virtual environment on Windows:

   `.\.venv\Scripts\Activate.ps1`

4. Install dependencies:

   `python -m pip install -r requirements.txt`

5. Start the server:

   `python -m uvicorn main:app --reload`

6. Open the interactive API documentation:

   `http://127.0.0.1:8000/docs`

Public repositories can be accessed without a GitHub token, subject to GitHub's API rate limits. For authenticated access, create a `.env` file containing `GITHUB_TOKEN=your_token`.

## API Endpoints

| Method | Endpoint | Description |
| GET | `/api/repos/{owner}/{repo}` | Retrieve repository information |
| GET | `/api/repos/{owner}/{repo}/issues` | List issues with optional state filtering |
| GET | `/api/repos/{owner}/{repo}/issues/{number}` | Retrieve a specific issue |
| GET | `/api/repos/{owner}/{repo}/files` | List and filter source files |
| GET | `/api/repos/{owner}/{repo}/file?path=...` | Read a source file |

## Next Development Tasks

-  Integrate an LLM API.
-  Create a service to send issue data to the model.
-  Generate structured issue-analysis responses.
-  Add tests for the AI analysis functionality.

## Project Status

Stage 1 completed. AI integration is the next development milestone.
