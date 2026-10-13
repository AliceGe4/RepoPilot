
import { useEffect, useState } from "react";

import {
  getRepository,
  getIssues,
  indexRepository,
  analyzeIssue,
  searchRepository,
  type RepositoryInfo,
  type GitHubIssue,
  type IndexResponse,
  type AnalysisResponse,
  type AnalysisMode,
  type SearchResponse,
} from "./api";

type Job = "issues" | "index" | "analysis" | "search" | null;

function App() {
  // Repository selection
  const [owner, setOwner] = useState("AliceGe4");
  const [repo, setRepo] = useState("RepoPilot");

  const [darkMode, setDarkMode] = useState<boolean>(() => {
  return localStorage.getItem("repopilot-theme") === "dark";
});

useEffect(() => {
  const theme = darkMode ? "dark" : "light";

  document.documentElement.setAttribute("data-theme", theme);

  localStorage.setItem("repopilot-theme", theme);
}, [darkMode]);

  // Data from FastAPI
  const [repositoryInfo, setRepositoryInfo] =
    useState<RepositoryInfo | null>(null);

  const [issues, setIssues] = useState<GitHubIssue[]>([]);
  const [indexInfo, setIndexInfo] =
    useState<IndexResponse | null>(null);

  const [analysis, setAnalysis] =
    useState<AnalysisResponse | null>(null);

  const [searchResult, setSearchResult] =
    useState<SearchResponse | null>(null);

  // Analysis settings
  const [issueNumber, setIssueNumber] = useState("1");

  const [mode, setMode] =
    useState<AnalysisMode>("automatic");

  const [filePaths, setFilePaths] = useState("main.py");
  const [topK, setTopK] = useState(3);

  // Semantic search
  const [query, setQuery] = useState(
    "GitHub issue pagination and pull request filtering"
  );

  // UI feedback
  const [job, setJob] = useState<Job>(null);
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const busy = job !== null;

  // Clear old data when changing repositories
  function resetResults() {
    setRepositoryInfo(null);
    setIssues([]);
    setIndexInfo(null);
    setAnalysis(null);
    setSearchResult(null);
    setIssueNumber("");
    setError("");
    setMessage("");
  }

  // Shared loading and error handling
  async function runJob(
    jobName: Exclude<Job, null>,
    operation: () => Promise<void>
  ) {
    setJob(jobName);
    setError("");
    setMessage("");

    try {
      await operation();
    } catch (err) {
      setError(
        err instanceof Error ? err.message : "Unexpected error"
      );
    } finally {
      setJob(null);
    }
  }

  // Retrieve repository metadata and open issues
  async function loadIssues() {
    if (!owner.trim() || !repo.trim()) {
      setError("Enter a repository owner and name.");
      return;
    }

    await runJob("issues", async () => {
      const [info, result] = await Promise.all([
        getRepository(owner.trim(), repo.trim()),
        getIssues(owner.trim(), repo.trim()),
      ]);

      setRepositoryInfo(info);
      setIssues(result.issues);

      if (result.issues.length > 0) {
        setIssueNumber(String(result.issues[0].number));
      }

      setMessage("Repository issues loaded successfully.");
    });
  }

  // Build the local RAG index
  async function buildRepositoryIndex() {
    await runJob("index", async () => {
      const result = await indexRepository(
        owner.trim(),
        repo.trim()
      );

      setIndexInfo(result);

      setMessage(
        `Indexed ${result.files_indexed} files and ` +
        `${result.chunks_indexed} code chunks.`
      );
    });
  }

  // Analyze a selected issue
  async function handleAnalyze() {
    const number = Number(issueNumber);

    if (!Number.isInteger(number) || number < 1) {
      setError("Enter a valid positive issue number.");
      return;
    }

    const paths = filePaths
      .split(",")
      .map((path) => path.trim())
      .filter(Boolean);

    if (mode === "manual" && (paths.length < 1 || paths.length > 3)) {
      setError("Manual mode requires 1 to 3 file paths.");
      return;
    }

    await runJob("analysis", async () => {
      setAnalysis(null);

      const result = await analyzeIssue(
        owner.trim(),
        repo.trim(),
        {
          issue_number: number,
          file_paths: mode === "manual" ? paths : [],
          auto_retrieve: mode === "automatic",
          top_k: topK,
        }
      );

      setAnalysis(result);
      setMessage("AI analysis completed.");
    });
  }

  // Search repository code using embeddings
  async function handleSearch() {
    if (query.trim().length < 3) {
      setError("Enter at least 3 characters to search.");
      return;
    }

    await runJob("search", async () => {
      setSearchResult(null);

      const result = await searchRepository(
        owner.trim(),
        repo.trim(),
        query.trim(),
        topK
      );

      setSearchResult(result);
    });
  }

  return (
    <main className="container">
      <header className="header">
        <div>
          <p className="eyebrow">AI DEVELOPER TOOL</p>
          <h1>RepoPilot</h1>
          <p className="subtitle">
            Investigate GitHub issues with semantic code search
            and locally hosted AI.
          </p>
        </div>
        
<div className="header-actions">
  <span className="model-tag">Ollama · Local AI</span>

  <label className="theme-switch">
    <input
      type="checkbox"
      role="switch"
      checked={darkMode}
      onChange={(e) => setDarkMode(e.target.checked)}
      aria-label="Dark mode"
    />

    <span className="switch-track" aria-hidden="true">
      <span className="switch-thumb"></span>
    </span>

    <span className="theme-label">
      {darkMode ? "Dark mode" : "Light mode"}
    </span>
  </label>
</div>

      </header>

      <section className="panel">
        <h2>1. Select a GitHub repository</h2>

        <div className="input-grid">
          <label>
            Repository owner
            <input
              value={owner}
              disabled={busy}
              onChange={(e) => {
                setOwner(e.target.value);
                resetResults();
              }}
              placeholder="e.g. AliceGe4"
            />
          </label>

          <label>
            Repository name
            <input
              value={repo}
              disabled={busy}
              onChange={(e) => {
                setRepo(e.target.value);
                resetResults();
              }}
              placeholder="e.g. RepoPilot"
            />
          </label>
        </div>

        <button disabled={busy} onClick={loadIssues}>
          {job === "issues" ? "Loading..." : "Load GitHub issues"}
        </button>

        {repositoryInfo && (
          <div className="repository-info">
            <strong>{repositoryInfo.name}</strong>
            <p>{repositoryInfo.description || "No description"}</p>
            <p>
              Language: {repositoryInfo.language || "Unknown"} ·
              Branch: {repositoryInfo.default_branch}
            </p>
            <a
              href={repositoryInfo.url}
              target="_blank"
              rel="noreferrer"
            >
              View on GitHub ↗
            </a>
          </div>
        )}
      </section>

      <div className="columns">
        <section className="panel">
          <h2>2. GitHub issues</h2>
          <p className="muted">
            Select an issue from the loaded results, or enter its
            number manually below.
          </p>

          {issues.length === 0 ? (
            <p className="empty">
              No issues loaded. Your repository may also have no
              open issues in the first results page.
            </p>
          ) : (
            <div className="issue-list">
              {issues.map((issue) => (
                <button
                  key={issue.number}
                  disabled={busy}
                  className={
                    issueNumber === String(issue.number)
                      ? "issue selected"
                      : "issue"
                  }
                  onClick={() => {
                    setIssueNumber(String(issue.number));
                    setAnalysis(null);
                  }}
                >
                  <span>#{issue.number}</span>
                  {issue.title}
                </button>
              ))}
            </div>
          )}
        </section>

        <section className="panel">
          <h2>3. Repository index</h2>
          <p className="muted">
            Build a local embedding index to enable automatic
            source-code retrieval.
          </p>

          <button
            disabled={busy}
            onClick={buildRepositoryIndex}
          >
            {job === "index"
              ? "Indexing repository..."
              : "Build / Rebuild Index"}
          </button>

          {indexInfo ? (
            <div className="repository-info">
              <strong>Index completed</strong>
              <p>Files indexed: {indexInfo.files_indexed}</p>
              <p>Chunks indexed: {indexInfo.chunks_indexed}</p>
              <p>Model: {indexInfo.embedding_model}</p>
              <p>Commit: {indexInfo.commit_sha.slice(0, 12)}</p>
            </div>
          ) : (
            <p className="muted small">
              If you've already indexed this repository in Swagger
              UI, the existing local index can still be used.
            </p>
          )}
        </section>
      </div>

      <section className="panel">
        <h2>4. Analyze a GitHub issue</h2>

        <div className="input-grid">
          <label>
            Issue number
            <input
              type="number"
              min="1"
              value={issueNumber}
              onChange={(e) => setIssueNumber(e.target.value)}
            />
          </label>

          <label>
            Analysis mode
            <select
              value={mode}
              onChange={(e) =>
                setMode(e.target.value as AnalysisMode)
              }
            >
              <option value="automatic">
                Automatic (RAG)
              </option>
              <option value="manual">
                Manual source files
              </option>
              <option value="issue_only">
                Issue description only
              </option>
            </select>
          </label>
        </div>

        {mode === "manual" && (
          <label>
            Source file paths (comma-separated)
            <input
              value={filePaths}
              onChange={(e) => setFilePaths(e.target.value)}
              placeholder="main.py, github_client.py"
            />
          </label>
        )}

        {mode === "automatic" && (
          <label>
            Number of retrieved chunks
            <select
              value={topK}
              onChange={(e) => setTopK(Number(e.target.value))}
            >
              <option value={1}>1</option>
              <option value={2}>2</option>
              <option value={3}>3</option>
              <option value={4}>4</option>
              <option value={5}>5</option>
            </select>
          </label>
        )}

        <button disabled={busy} onClick={handleAnalyze}>
          {job === "analysis"
            ? "AI is analyzing..."
            : "Analyze with AI"}
        </button>

        <p className="muted small">
          Automatic mode requires an existing repository index.
          Manual and issue-only modes do not.
        </p>
      </section>

      {error && (
        <div className="notification error" role="alert">
          {error}
        </div>
      )}

      {message && (
        <div className="notification success" role="status">
          {message}
        </div>
      )}

      {analysis && (
        <section className="panel results">
          <p className="eyebrow">AI ANALYSIS</p>
          <h2>
            Issue #{analysis.issue_number} — {analysis.repository}
          </h2>

          <div className="result-block">
            <h3>Summary</h3>
            <p>{analysis.analysis.summary}</p>
          </div>

          <div className="result-block">
            <h3>Possible cause</h3>
            <p>{analysis.analysis.possible_cause}</p>
          </div>

          <div className="result-block">
            <h3>Suggested debugging steps</h3>
            <ol>
              {analysis.analysis.debugging_steps.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          </div>

          <div className="result-block">
            <h3>Confidence</h3>
            <p>{analysis.analysis.confidence}</p>
          </div>

          <div className="result-block">
            <h3>Limitations</h3>
            <p>{analysis.analysis.limitations}</p>
          </div>

          <div className="result-block">
            <h3>Retrieved source code</h3>
            <p className="muted">
              Retrieval mode: {analysis.retrieval.mode}
            </p>

            {analysis.retrieval.chunks.length > 0 ? (
              analysis.retrieval.chunks.map((chunk, i) => (
                <div key={i} className="code-reference">
                  <strong>{chunk.path}</strong>
                  <span>
                    Lines {chunk.start_line}–{chunk.end_line}
                  </span>
                  <span>
                    Similarity: {chunk.similarity_score.toFixed(4)}
                  </span>
                </div>
              ))
            ) : (
              <p className="muted">
                No semantic retrieval chunks for this analysis.
              </p>
            )}
          </div>

          <p className="muted small">
            Model: {analysis.model}
            {analysis.token_usage &&
              ` · Input tokens: ${analysis.token_usage.input_tokens ?? "N/A"}` +
              ` · Output tokens: ${analysis.token_usage.output_tokens ?? "N/A"}`}
          </p>
        </section>
      )}

      <section className="panel">
        <h2>5. Semantic code search</h2>
        <p className="muted">
          Search the indexed repository using a natural-language
          description of the code you're looking for.
        </p>

        <label>
          Search query
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Find GitHub issue pagination logic"
          />
        </label>

        <button disabled={busy} onClick={handleSearch}>
          {job === "search" ? "Searching..." : "Search source code"}
        </button>

        {searchResult && (
          <div className="search-results">
            <h3>Search results</h3>

            {searchResult.matches.map((match, i) => (
              <div className="code-match" key={i}>
                <strong>{match.path}</strong>
                <p className="muted small">
                  Lines {match.start_line}–{match.end_line} ·
                  Similarity: {match.score.toFixed(4)}
                </p>
                <pre><code>{match.code}</code></pre>
              </div>
            ))}
          </div>
        )}
      </section>

      <footer>
        RepoPilot · Python · FastAPI · React · TypeScript · Ollama
      </footer>
    </main>
  );
}

export default App;
