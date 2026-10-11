import os

import httpx
from dotenv import load_dotenv
from fastapi import HTTPException

# Load environment variables from .env
load_dotenv()

GITHUB_API_URL = "https://api.github.com"

# Headers tell GitHub what kind of request we're making
HEADERS = {
    "Accept": "application/vnd.github+json",
    "X-GitHub-Api-Version": "2026-03-10",
}

# Authentication is optional for public repositories
token = os.getenv("GITHUB_TOKEN")

if token:
    HEADERS["Authorization"] = f"Bearer {token}"


async def github_get(endpoint: str, params: dict | None = None):
    """
    Send a GET request to GitHub and return JSON data.
    """

    try:
        async with httpx.AsyncClient(
            base_url=GITHUB_API_URL,
            headers=HEADERS,
            timeout=15.0,
        ) as client:
            response = await client.get(endpoint, params=params)

    except httpx.RequestError as error:
        raise HTTPException(
            status_code=502,
            detail="Could not connect to GitHub."
        ) from error

    # Handle common GitHub errors
    if response.status_code == 404:
        raise HTTPException(
            status_code=404,
            detail="GitHub resource not found."
        )

    if response.status_code == 401:
        raise HTTPException(
            status_code=401,
            detail="GitHub authentication failed. Check your token."
        )

    if response.status_code in (403, 429):
        raise HTTPException(
            status_code=429 if response.headers.get(
                "x-ratelimit-remaining"
            ) == "0" or response.status_code == 429 else 502,
            detail="GitHub denied the request. Check your API limits and permissions."
        )

    if response.is_error:
        raise HTTPException(
            status_code=502,
            detail=f"GitHub returned HTTP {response.status_code}."
        )

    return response.json()