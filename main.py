
import base64
import binascii
from urllib.parse import quote
from typing import Literal
from ai_analyzer import AnalysisRequest, analyze_github_issue

from fastapi import FastAPI, HTTPException, Query
from github_client import github_get

from rag_engine import build_index, search_code
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(title="RepoPilot API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173"
    ],
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"]
)

# File types we want to inspect
SOURCE_EXTENSIONS = (
    ".py", ".java", ".js", ".jsx", ".ts", ".tsx",
    ".c", ".cpp", ".h", ".hpp", ".cs", ".go",
    ".rs", ".rb", ".html", ".css", ".sql",
    ".json", ".yaml", ".yml", ".md"
)


def repo_path(owner: str, repo: str):
    return f"/repos/{quote(owner, safe='')}/{quote(repo, safe='')}"


@app.get("/")
async def home():
    return {"message": "RepoPilot is running!"}


# Get repository information get allows us to leave areas as blank. As such Name must be filled while description can be null
@app.get("/api/repos/{owner}/{repo}")
async def get_repository(owner: str, repo: str):
    data = await github_get(repo_path(owner, repo))

    return {
        "name": data["full_name"],
        "description": data.get("description"),
        "default_branch": data["default_branch"],
        "url": data["html_url"],
        "language": data.get("language"),
    }


# List open issues

@app.get("/api/repos/{owner}/{repo}/issues")
async def get_issues(
    owner: str,
    repo: str,
    limit: int = Query(default=20, ge=1, le=100),
    state: Literal["open", "closed", "all"] = "open"
):
    data = await github_get(
        f"{repo_path(owner, repo)}/issues",
        params={
            "state": state,
            "per_page": limit,
            "page": 1
        }
    )

    issues = [
        {
            "number": issue["number"],
            "title": issue["title"],
            "body": issue.get("body"),
            "state": issue["state"],
            "url": issue["html_url"]
        }
        for issue in data
        if "pull_request" not in issue
    ]

    return {
        "repository": f"{owner}/{repo}",
        "count": len(issues),
        "issues": issues
    }

#Handles specific issue

@app.get("/api/repos/{owner}/{repo}/issues/{number}")
async def get_issue(
    owner: str,
    repo: str,
    number: int
):
    # Validate issue number
    if number <= 0:
        raise HTTPException(
            status_code=400,
            detail="Issue number must be positive."
        )

    # Request a specific issue from GitHub
    data = await github_get(
        f"{repo_path(owner, repo)}/issues/{number}"
    )

    # GitHub also represents pull requests as issues
    if "pull_request" in data:
        raise HTTPException(
            status_code=400,
            detail="This number belongs to a pull request."
        )

    return {
        "repository": f"{owner}/{repo}",
        "number": data["number"],
        "title": data["title"],
        "body": data.get("body"),
        "state": data["state"],
        "created_at": data["created_at"],
        "url": data["html_url"]
    }



# List repository source files

@app.get(
    "/api/repos/{owner}/{repo}/files",
    summary="List repository source files",
    tags=["Repository Files"]
)
async def list_repository_files(
    owner: str,
    repo: str,
    extension: str | None = None
):
    base = repo_path(owner, repo)

    repository = await github_get(base)
    branch = repository["default_branch"]

    commit = await github_get(
        f"{base}/commits/{quote(branch, safe='')}"
    )

    tree_sha = commit["commit"]["tree"]["sha"]

    tree = await github_get(
        f"{base}/git/trees/{tree_sha}",
        params={"recursive": "1"}
    )

    files = [
        {
            "path": item["path"],
            "size": item.get("size", 0)
        }
        for item in tree["tree"]
        if item["type"] == "blob"
        and item["path"].lower().endswith(SOURCE_EXTENSIONS)
    ]

    # NEW: Filter by extension if provided
    if extension:
        extension = extension.lower()

        # Allow users to enter "py" or ".py"
        if not extension.startswith("."):
            extension = "." + extension

        if extension not in SOURCE_EXTENSIONS:
            raise HTTPException(
                status_code=400,
                detail="Unsupported file extension."
            )

        files = [
            file for file in files
            if file["path"].lower().endswith(extension)
        ]

    return {
        "repository": f"{owner}/{repo}",
        "extension": extension,
        "total_matching_files": len(files),
        "files": files[:200],
        "limited": len(files) > 200,
        "github_tree_truncated": tree.get("truncated", False)
    }

    # Keep only source files and other useful text files
    files = [
        {
            "path": item["path"],
            "size": item.get("size", 0)
        }
        for item in tree["tree"]
        if item["type"] == "blob"
        and item["path"].lower().endswith(SOURCE_EXTENSIONS)
    ]

    # Cap the output to keep this first version small
    return {
        "repository": f"{owner}/{repo}",
        "total_matching_files": len(files),
        "files": files[:200],
        "limited": len(files) > 200,
        "github_tree_truncated": tree.get("truncated", False)
    }


# Read a specific file
@app.get(
    "/api/repos/{owner}/{repo}/files/content",
    summary="Read source file contents",
    tags=["Repository Files"]
)
async def read_repository_file(
    owner: str,
    repo: str,
    path: str = Query(min_length=1)
):
    # Reject invalid paths
    if (
        path.startswith("/")
        or any(part in ("", ".", "..") for part in path.split("/"))
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid file path."
        )

    encoded_path = quote(path, safe="/")

    data = await github_get(
        f"{repo_path(owner, repo)}/contents/{encoded_path}"
    )

    if not isinstance(data, dict) or data.get("type") != "file":
        raise HTTPException(
            status_code=400,
            detail="Path is not a regular file."
        )

    # Avoid downloading very large files for now
    if data.get("size", 0) > 200_000:
        raise HTTPException(
            status_code=413,
            detail="File is too large for this version."
        )

    if data.get("encoding") != "base64":
        raise HTTPException(
            status_code=415,
            detail="Unsupported file encoding."
        )

    try:
        content = base64.b64decode(
            data["content"]
        ).decode("utf-8")
    except (UnicodeDecodeError, binascii.Error, KeyError):
        raise HTTPException(
            status_code=415,
            detail="Could not decode this file as UTF-8 text."
        )

    return {
        "path": data["path"],
        "size": data["size"],
        "content": content,
        "url": data["html_url"]
    }


@app.post("/api/repos/{owner}/{repo}/analyze")
async def analyze_issue_endpoint(
    owner: str,
    repo: str,
    request: AnalysisRequest
):
    return await analyze_github_issue(
        owner,
        repo,
        request
    )



# Build a searchable repository index
@app.post(
    "/api/repos/{owner}/{repo}/index",
    summary="Index repository source code",
    tags=["Semantic Search"]
)
async def index_repository_endpoint(
    owner: str,
    repo: str
):
    return await build_index(owner, repo)


# Search the indexed source code
@app.get(
    "/api/repos/{owner}/{repo}/search",
    summary="Search repository code by meaning",
    tags=["Semantic Search"]
)
async def search_repository_endpoint(
    owner: str,
    repo: str,
    query: str = Query(min_length=3, max_length=600),
    top_k: int = Query(default=3, ge=1, le=5)
):
    return await search_code(
        owner,
        repo,
        query,
        top_k
    )

