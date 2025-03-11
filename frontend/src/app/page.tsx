"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  loadRepository, 
  getRepositoryStatus, 
  queryRepository, 
  getRepositorySummary,
  RepositoryStatus 
} from "@/lib/api-service";

interface RepoStatusState {
  loaded: boolean;
  ready: boolean;
  details?: {
    stage: string;
    message: string;
    progress?: {
      total_files: number;
      processed_files: number;
      skipped_files: number;
      chunks_created: number;
    };
    error?: string;
  };
}

function formatStage(stage: string): string {
  const stageMap: { [key: string]: string } = {
    'initializing': 'Initializing',
    'cloning': 'Cloning Repository',
    'scanning': 'Scanning Files',
    'processing': 'Processing Files',
    'storing': 'Storing Data',
    'ready': 'Ready',
    'error': 'Error',
    'queued': 'Queued'
  };
  return stageMap[stage] || stage;
}

function getStatusText(status: any): string {
  if (!status.loaded) return "Not Loaded";
  if (status.details?.error) return "Error";
  if (status.ready) return "Ready";
  if (status.details?.stage) return formatStage(status.details.stage);
  return "Processing...";
}

export default function Home() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [repoStatus, setRepoStatus] = useState<RepoStatusState>({ loaded: false, ready: false });
  const [activeRepo, setActiveRepo] = useState("");
  const [answer, setAnswer] = useState("");
  const [summary, setSummary] = useState("");
  const [tab, setTab] = useState("query"); // "query" or "summary"

  // Check repository status periodically if one is loading
  useEffect(() => {
    if (!activeRepo) return;

    const checkStatus = async () => {
      try {
        const status = await getRepositoryStatus(activeRepo);
        
        // Update the status state
        setRepoStatus({
          loaded: status.loaded,
          ready: status.status === "ready" || status.status === "error",
          details: {
            stage: status.status,
            message: status.details.message,
            progress: status.details.progress,
            error: status.details.error
          }
        });
        
        // If there's an error or the status is ready, stop polling
        if (status.status === "error" || status.status === "ready") {
          if (status.status === "error") {
            setError(status.details.message || "An error occurred while processing the repository");
          }
          return;
        }
        
        // Log processing status
        if (status.details?.stage && status.details?.message) {
          console.log(`Processing: ${status.details.stage} - ${status.details.message}`);
        }
      } catch (err) {
        console.error("Error checking repository status:", err);
        setError("Failed to check repository status");
        setRepoStatus(prev => ({ ...prev, ready: true })); // Stop polling on error
      }
    };
    
    // Check immediately
    checkStatus();
    
    // Then check every 5 seconds if not ready
    const interval = setInterval(() => {
      if (!repoStatus.ready) {
        checkStatus();
      }
    }, 5000);
    
    // Cleanup interval on unmount or when activeRepo changes
    return () => clearInterval(interval);
  }, [activeRepo]);

  const handleSubmitRepo = async (e: React.FormEvent | null, forceReload: boolean = false) => {
    if (e) e.preventDefault();
    if (!repoUrl && !activeRepo) return;
    
    setLoading(true);
    setError("");
    
    try {
      // Use repoUrl for new submissions, only fallback to activeRepo if repoUrl is empty
      const urlToUse = repoUrl || activeRepo;
      const response = await loadRepository(urlToUse, forceReload);
      
      if (response.success) {
        setActiveRepo(urlToUse);
        setRepoStatus({ loaded: true, ready: false });
        // Clear the answer and summary when changing repositories
        setAnswer("");
        setSummary("");
      } else {
        setError(response.message || "Failed to load repository");
      }
    } catch (err) {
      console.error(err);
      setError("An error occurred while loading the repository");
    } finally {
      setLoading(false);
    }
  };

  const handleSubmitQuery = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!query || !repoStatus.ready) return;
    
    setLoading(true);
    setError("");
    
    try {
      const response = await queryRepository(activeRepo, query);
      setAnswer(response.answer);
    } catch (err) {
      console.error(err);
      setError("An error occurred while querying the repository");
    } finally {
      setLoading(false);
    }
  };

  const handleFetchSummary = async () => {
    if (!repoStatus.ready) return;
    
    setLoading(true);
    setError("");
    
    try {
      const response = await getRepositorySummary(activeRepo);
      setSummary(response.summary);
    } catch (err) {
      console.error(err);
      setError("An error occurred while generating the repository summary");
    } finally {
      setLoading(false);
    }
  };

  // When switching to summary tab, fetch the summary if not already loaded
  useEffect(() => {
    if (tab === "summary" && repoStatus.ready && !summary && !loading) {
      handleFetchSummary();
    }
  }, [tab, repoStatus.ready, summary, loading]);

  return (
    <main className="flex min-h-screen flex-col p-6 md:p-12 max-w-6xl mx-auto">
      <header className="mb-12">
        <h1 className="text-4xl font-bold text-center">GitSummarizer-RAG</h1>
        <p className="text-xl text-center text-gray-600 mt-2">
          Analyze GitHub repositories with natural language queries
        </p>
      </header>

      {/* Repository URL Input */}
      <section className="mb-10">
        <form onSubmit={(e) => handleSubmitRepo(e, false)} className="flex flex-col md:flex-row gap-4">
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="Enter GitHub repository URL (e.g., https://github.com/username/repo)"
            className="flex-grow p-3 border rounded-lg"
            disabled={loading}
          />
          <div className="flex gap-2">
            <button
              type="submit"
              className="bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
              disabled={loading || !repoUrl}
            >
              {loading ? "Loading..." : activeRepo ? "Change Repository" : "Load Repository"}
            </button>
            {activeRepo && (
              <button
                type="button"
                onClick={() => {
                  setActiveRepo("");
                  setRepoUrl("");
                  setRepoStatus({ loaded: false, ready: false });
                  setAnswer("");
                  setSummary("");
                  setError("");
                }}
                className="bg-gray-200 text-gray-700 p-3 rounded-lg hover:bg-gray-300 transition-colors"
                disabled={loading}
              >
                Clear
              </button>
            )}
          </div>
        </form>
      </section>

      {/* Repository Status */}
      {activeRepo && (
        <section className="mb-8 p-4 border rounded-lg bg-gray-50">
          <div className="flex items-center justify-between">
            <div className="flex-grow">
              <h2 className="text-lg font-semibold">Repository: {activeRepo}</h2>
              <p className="text-sm text-gray-600 mb-2">
                Status: {getStatusText(repoStatus)}
              </p>
              {repoStatus.loaded && !repoStatus.ready && (
                <div className="mt-2">
                  <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                    <div 
                      className="h-full bg-blue-600 transition-all duration-500"
                      style={{ 
                        width: repoStatus.details?.progress?.processed_files && repoStatus.details?.progress?.total_files
                          ? `${(repoStatus.details.progress.processed_files / repoStatus.details.progress.total_files) * 100}%`
                          : '0%'
                      }}
                    />
                  </div>
                  <p className="text-sm text-gray-600 mt-1">
                    {repoStatus.details?.stage && `${formatStage(repoStatus.details.stage)}: `}
                    {repoStatus.details?.message}
                  </p>
                  {repoStatus.details?.progress && (
                    <p className="text-xs text-gray-500 mt-1">
                      Processed {repoStatus.details.progress.processed_files} of {repoStatus.details.progress.total_files} files
                      {repoStatus.details.progress.chunks_created > 0 && 
                        ` • ${repoStatus.details.progress.chunks_created} chunks created`}
                    </p>
                  )}
                </div>
              )}
            </div>
            <div className="flex gap-2">
              {repoStatus.ready ? (
                <>
                  <button
                    onClick={() => setTab("query")}
                    className={`px-4 py-2 rounded-md ${
                      tab === "query" ? "bg-blue-600 text-white" : "bg-gray-200"
                    }`}
                  >
                    Query
                  </button>
                  <button
                    onClick={() => setTab("summary")}
                    className={`px-4 py-2 rounded-md ${
                      tab === "summary" ? "bg-blue-600 text-white" : "bg-gray-200"
                    }`}
                  >
                    Summary
                  </button>
                </>
              ) : (
                <button
                  onClick={() => handleSubmitRepo(null, true)}
                  className="px-4 py-2 rounded-md bg-gray-200 hover:bg-gray-300"
                  disabled={loading}
                >
                  Retry
                </button>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Error Message */}
      {error && (
        <div className="mb-6 p-4 bg-red-100 border border-red-300 text-red-700 rounded-lg">
          {error}
        </div>
      )}

      {/* Main Content Area */}
      {repoStatus.ready && (
        <section className="mb-6">
          {tab === "query" ? (
            <div>
              <form onSubmit={handleSubmitQuery} className="space-y-4">
                <div>
                  <label htmlFor="query" className="block text-sm font-medium text-gray-700 mb-2">
                    Ask a question about your repository
                  </label>
                  <textarea
                    id="query"
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        handleSubmitQuery(e as any);
                      }
                    }}
                    className="w-full p-3 border rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
                    placeholder="Enter your question here..."
                    rows={3}
                  />
                </div>
                <div className="flex justify-end">
                  <button
                    type="submit"
                    disabled={!query.trim() || loading}
                    className="px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {loading ? 'Querying...' : 'Submit Query'}
                  </button>
                </div>
              </form>
              {answer && (
                <div className="mt-6 p-4 border rounded-lg bg-gray-50">
                  <h3 className="font-semibold mb-2">Answer:</h3>
                  <p className="whitespace-pre-wrap">{answer}</p>
                </div>
              )}
            </div>
          ) : (
            <div>
              {loading ? (
                <div className="flex justify-center items-center h-64">
                  <p className="text-xl text-gray-600">Generating summary...</p>
                </div>
              ) : summary ? (
                <div className="p-4 bg-gray-50 border rounded-lg">
                  <h3 className="font-semibold text-xl mb-4">Repository Summary</h3>
                  <div className="prose max-w-none">
                    {summary.split("\n").map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
                </div>
              ) : (
                <div className="flex justify-center items-center h-64">
                  <p className="text-xl text-gray-600">No summary available</p>
                </div>
              )}
            </div>
          )}
        </section>
      )}

      {/* Loading Repository Message */}
      {activeRepo && !repoStatus.ready && (
        <div className="flex flex-col items-center justify-center h-64">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-700 mb-4"></div>
          <p className="text-xl text-gray-600">
            Loading and processing repository...
          </p>
          <p className="text-sm text-gray-500 mt-2">
            This may take a few minutes for larger repositories
          </p>
        </div>
      )}

      {/* Intro Message */}
      {!activeRepo && (
        <div className="p-8 bg-gray-50 border rounded-lg">
          <h3 className="text-xl font-semibold mb-4 text-center">
            Welcome to GitSummarizer-RAG
          </h3>
          <p className="text-center mb-4">
            Analyze any GitHub repository using natural language. Just enter the repository URL above to get started.
          </p>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-8">
            <div className="p-4 border rounded-lg bg-white">
              <h4 className="font-semibold">Ask Questions About Code</h4>
              <p className="text-sm text-gray-600 mt-2">
                Query any aspect of the repository with natural language questions
              </p>
            </div>
            <div className="p-4 border rounded-lg bg-white">
              <h4 className="font-semibold">Get Repository Summaries</h4>
              <p className="text-sm text-gray-600 mt-2">
                Understand the main components and architecture at a glance
              </p>
            </div>
          </div>
        </div>
      )}
    </main>
  );
}
