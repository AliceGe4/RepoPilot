
import os
import json
import math
import base64
import binascii
import hashlib
from pathlib import Path
from urllib.parse import quote

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException
from ollama import AsyncClient, ResponseError

from github_client import github_get


load_dotenv()

EMBEDDING_MODEL = os.getenv(
    "EMBEDDING_MODEL", "nomic-embed-text"
)

CACHE_DIR = Path(__file__).resolve().parent / ".repopilot_cache"

SOURCE_EXTENSIONS = (
    ".py", ".java", ".js", ".jsx",
    ".ts", ".tsx", ".c", ".cpp",
    ".h", ".hpp", ".cs", ".go", ".rs"
)

EXCLUDED_DIRECTORIES = {
    ".venv", "venv", "node_modules",
    "__pycache__", "dist", "build",
    ".git", ".next"
}

MAX_FILES = 30
MAX_FILE_BYTES = 12_000
MAX_CHUNKS = 120

CHUNK_LINES = 30
CHUNK_OVERLAP = 5
MAX_CHUNK_CHARS = 1600


def repo_base(owner: str, repo: str) -> str:
    return (
        f"/repos/{quote(owner, safe='')}"
        f"/{quote(repo, safe='')}"
    )


def cache_path(owner: str, repo: str) -> Path:
    identity = f"{owner.lower()}/{repo.lower()}"
    key = hashlib.sha256(identity.encode()).hexdigest()[:20]
    return CACHE_DIR / f"{key}.json"


def chunk_source(path: str, content: str) -> list[dict]:
    lines = content.splitlines()
    chunks = []

    start = 0

    while start < len(lines):
        selected = []
        char_count = 0

        # Add up to CHUNK_LINES lines, respecting our size limit
        for line in lines[start:start + CHUNK_LINES]:
            remaining = MAX_CHUNK_CHARS - char_count

            if remaining <= 0:
                break

            if len(line) + 1 > remaining:
                if not selected:
                    # Handle an exceptionally long single line
                    selected.append(line[:MAX_CHUNK_CHARS])
                break

            selected.append(line)
            char_count += len(line) + 1

        if not selected:
            break

        end = start + len(selected)

        text = "\n".join(selected)

        if text.strip():
            chunks.append({
                "path": path,
                "start_line": start + 1,
                "end_line": end,
                "text": text
            })

        if end >= len(lines):
            break

        # Move forward while keeping a little overlap
        start = max(start + 1, end - CHUNK_OVERLAP)

    return chunks


async def discover_source_files(owner: str, repo: str):
    base = repo_base(owner, repo)

    # Retrieve default branch information
    repository = await github_get(base)
    branch = repository["default_branch"]

    # Find the current commit
    commit = await github_get(
        f"{base}/commits/{quote(branch, safe='')}"
    )

    # Find the associated Git tree
    tree_sha = commit["commit"]["tree"]["sha"]

    tree = await github_get(
        f"{base}/git/trees/{tree_sha}",
        params={"recursive": "1"}
    )

    if tree.get("truncated"):
        raise HTTPException(
            status_code=422,
            detail="Repository tree is too large for this indexer."
        )

    files = []

    for item in tree["tree"]:
        if item["type"] != "blob":
            continue

        path = item["path"]

        # Skip dependency directories and generated files
        directories = set(path.split("/")[:-1])

        if directories & EXCLUDED_DIRECTORIES:
            continue

        if not path.lower().endswith(SOURCE_EXTENSIONS):
            continue

        size = item.get("size", 0)

        if not (0 < size <= MAX_FILE_BYTES):
            continue

        files.append(item)

    files.sort(key=lambda file: file["path"])

    return {
        "commit_sha": commit["sha"],
        "files": files,
    }



async def read_blob(owner: str, repo: str, sha: str) -> str:
    base = repo_base(owner, repo)

    data = await github_get(
        f"{base}/git/blobs/{sha}"
    )

    if data.get("encoding") != "base64":
        raise HTTPException(
            status_code=415,
            detail="Unsupported Git blob encoding."
        )

    try:
        return base64.b64decode(
            data["content"]
        ).decode("utf-8")

    except (KeyError, ValueError, UnicodeError, binascii.Error):
        raise HTTPException(
            status_code=415,
            detail="Could not decode the source file."
        )

async def build_index(owner: str, repo: str):
    repository = await discover_source_files(owner, repo)

    # Keep this first version small
    selected_files = repository["files"][:MAX_FILES]

    chunks = []
    indexed_files = []

    # 1. Download and split each selected source file
    for file in selected_files:
        try:
            content = await read_blob(
                owner, repo, file["sha"]
            )
        except HTTPException as error:
            if error.status_code == 415:
                continue
            raise

        file_chunks = chunk_source(file["path"], content)

        remaining = MAX_CHUNKS - len(chunks)

        if remaining <= 0:
            break

        if not file_chunks:
            continue

        chunks.extend(file_chunks[:remaining])
        indexed_files.append(file["path"])

        if len(chunks) >= MAX_CHUNKS:
            break

    if not chunks:
        raise HTTPException(
            status_code=422,
            detail="No suitable source code was found."
        )

    # 2. Generate embeddings in small batches
    try:
        async with AsyncClient(timeout=120.0) as client:

            batch_size = 8

            for i in range(0, len(chunks), batch_size):
                batch = chunks[i:i + batch_size]

                texts = [
                    f"File: {chunk['path']}\n"
                    f"Lines: {chunk['start_line']}-{chunk['end_line']}\n"
                    f"{chunk['text']}"
                    for chunk in batch
                ]

                response = await client.embed(
                    model=EMBEDDING_MODEL,
                    input=texts
                )

                if len(response.embeddings) != len(batch):
                    raise HTTPException(
                        status_code=502,
                        detail="Unexpected number of embeddings."
                    )

                for chunk, vector in zip(
                    batch, response.embeddings
                ):
                    chunk["embedding"] = list(vector)

    except httpx.TimeoutException as error:
        raise HTTPException(
            status_code=504,
            detail="Embedding model timed out."
        ) from error

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama."
        ) from error

    except ResponseError as error:
        raise HTTPException(
            status_code=502,
            detail="Ollama failed to generate embeddings."
        ) from error

    # 3. Save the index locally
    index_data = {
        "repository": f"{owner}/{repo}",
        "commit_sha": repository["commit_sha"],
        "embedding_model": EMBEDDING_MODEL,
        "chunks": chunks
    }

    CACHE_DIR.mkdir(parents=True, exist_ok=True)

    destination = cache_path(owner, repo)
    temporary = destination.with_suffix(".tmp")

    temporary.write_text(
        json.dumps(index_data),
        encoding="utf-8"
    )

    temporary.replace(destination)

    return {
        "repository": f"{owner}/{repo}",
        "commit_sha": repository["commit_sha"],
        "files_indexed": len(indexed_files),
        "chunks_indexed": len(chunks),
        "embedding_model": EMBEDDING_MODEL,
        "file_limit_reached": len(repository["files"]) > MAX_FILES,
        "chunk_limit_reached": len(chunks) >= MAX_CHUNKS
    }

    
def cosine_similarity(a: list[float], b: list[float]) -> float:

    if not a or not b or len(a) != len(b):
        return 0.0

    # Dot product
    dot_product = sum(
        x * y for x, y in zip(a, b)
    )

    # Length of each vector
    magnitude_a = math.sqrt(
        sum(x * x for x in a)
    )

    magnitude_b = math.sqrt(
        sum(y * y for y in b)
    )

    if magnitude_a == 0 or magnitude_b == 0:
        return 0.0

    return dot_product / (magnitude_a * magnitude_b)

    
async def search_code(
    owner: str,
    repo: str,
    query: str,
    top_k: int = 3
):
    # 1. Find the local index
    index_file = cache_path(owner, repo)

    if not index_file.exists():
        raise HTTPException(
            status_code=404,
            detail="Repository not indexed. Run the index endpoint first."
        )

    index_data = json.loads(
        index_file.read_text(encoding="utf-8")
    )

    if index_data["embedding_model"] != EMBEDDING_MODEL:
        raise HTTPException(
            status_code=409,
            detail="Embedding model changed. Rebuild the index."
        )

    # 2. Generate an embedding for the search query
    try:
        async with AsyncClient(timeout=120.0) as client:
            response = await client.embed(
                model=EMBEDDING_MODEL,
                input=query
            )

    except httpx.TimeoutException as error:
        raise HTTPException(
            status_code=504,
            detail="Embedding model timed out."
        ) from error

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=503,
            detail="Cannot connect to Ollama."
        ) from error

    except ResponseError as error:
        raise HTTPException(
            status_code=502,
            detail="Could not generate query embedding."
        ) from error

    query_embedding = response.embeddings[0]

    # 3. Compare the query with every stored chunk
    results = []

    for chunk in index_data["chunks"]:
        similarity = cosine_similarity(
            query_embedding,
            chunk["embedding"]
        )

        results.append({
            "path": chunk["path"],
            "start_line": chunk["start_line"],
            "end_line": chunk["end_line"],
            "score": similarity,
            "code": chunk["text"]
        })

    # 4. Sort highest similarity first
    results.sort(
        key=lambda result: result["score"],
        reverse=True
    )

    # 5. Return the best results
    matches = results[:top_k]

    for match in matches:
        match["score"] = round(match["score"], 4)

    return {
        "repository": index_data["repository"],
        "indexed_commit": index_data["commit_sha"],
        "query": query,
        "embedding_model": EMBEDDING_MODEL,
        "matches": matches
    }
