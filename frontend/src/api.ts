
const API_URL = "http://127.0.0.1:8000";

// -------------------------
// DATA TYPES
// -------------------------

export interface RepositoryInfo {
  name: string;
  description: string | null;
  default_branch: string;
  url: string;
  language: string | null;
}

export interface GitHubIssue {
  number: number;
  title: string;
  body: string | null;
  url: string;
  state?: string;
}

export interface IssueListResponse {
  repository: string;
  count: number;
  issues: GitHubIssue[];
}

export interface IndexResponse {
  repository: string;
  commit_sha: string;
  files_indexed: number;
  chunks_indexed: number;
  embedding_model: string;
}

export interface CodeMatch {
  path: string;
  start_line: number;
  end_line: number;
  score: number;
  code: string;
}

export interface SearchResponse {
  repository: string;
  indexed_commit: string;
  query: string;
  embedding_model: string;
  matches: CodeMatch[];
}

export type AnalysisMode =
  | "automatic"
  | "manual"
  | "issue_only";

export interface AnalysisRequest {
  issue_number: number;
  file_paths: string[];
  auto_retrieve: boolean;
  top_k: number;
}

export interface AnalysisResponse {
  repository: string;
  issue_number: number;
  files_used: string[];

  retrieval: {
    mode: string;
    indexed_commit: string | null;
    chunks: {
      path: string;
      start_line: number;
      end_line: number;
      similarity_score: number;
    }[];
  };

  model: string;

  analysis: {
    summary: string;
    possible_cause: string;
    debugging_steps: string[];
    confidence: string;
    limitations: string;
  };

  token_usage: {
    input_tokens: number | null;
    output_tokens: number | null;
  } | null;
}

// -------------------------
// HTTP REQUEST HELPER
// -------------------------

async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  let response: Response;

  try {
    response = await fetch(`${API_URL}${path}`, {
      ...options,
      headers: options.body
        ? { "Content-Type": "application/json" }
        : undefined,
    });
  } catch {
    throw new Error(
      "Cannot reach FastAPI. Is the backend running on port 8000?"
    );
  }

  const data: unknown = await response
    .json()
    .catch(() => null);

  if (!response.ok) {
    let detail = response.statusText;

    if (data && typeof data === "object" && "detail" in data) {
      const value = data.detail;

      if (typeof value === "string") {
        detail = value;
      }
    }

    throw new Error(`${response.status}: ${detail}`);
  }

  return data as T;
}

// -------------------------
// REPOSITORY URL HELPER
// -------------------------

function repoPath(owner: string, repo: string): string {
  return (
    `/api/repos/${encodeURIComponent(owner)}` +
    `/${encodeURIComponent(repo)}`
  );
}

// -------------------------
// BACKEND API FUNCTIONS
// -------------------------

export function getRepository(owner: string, repo: string) {
  return apiRequest<RepositoryInfo>(
    repoPath(owner, repo)
  );
}

export function getIssues(owner: string, repo: string) {
  return apiRequest<IssueListResponse>(
    `${repoPath(owner, repo)}/issues?limit=30&state=open`
  );
}

export function indexRepository(owner: string, repo: string) {
  return apiRequest<IndexResponse>(
    `${repoPath(owner, repo)}/index`,
    { method: "POST" }
  );
}

export function analyzeIssue(
  owner: string,
  repo: string,
  request: AnalysisRequest
) {
  return apiRequest<AnalysisResponse>(
    `${repoPath(owner, repo)}/analyze`,
    {
      method: "POST",
      body: JSON.stringify(request),
    }
  );
}

export function searchRepository(
  owner: string,
  repo: string,
  query: string,
  topK: number
) {
  const parameters = new URLSearchParams({
    query,
    top_k: String(topK),
  });

  return apiRequest<SearchResponse>(
    `${repoPath(owner, repo)}/search?${parameters}`
  );
}
