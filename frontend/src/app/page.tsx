"use client";

import { useState, useEffect } from "react";
import { useRouter } from "next/navigation";
import { 
  loadRepository, 
  getRepositoryStatus, 
  queryRepository, 
  getRepositorySummary 
} from "@/lib/api-service";

export default function Home() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [repoStatus, setRepoStatus] = useState({ loaded: false, ready: false });
  const [activeRepo, setActiveRepo] = useState("");
  const [answer, setAnswer] = useState("");
  const [summary, setSummary] = useState("");
  const [tab, setTab] = useState("query"); // "query" or "summary"

  // Check repository status periodically if one is loading
  useEffect(() => {
    if (activeRepo && !repoStatus.ready) {
      const checkStatus = async () => {
        const status = await getRepositoryStatus(activeRepo);
        setRepoStatus(status);
      };
      
      // Check immediately
      checkStatus();
      
      // Then check every 5 seconds
      const interval = setInterval(checkStatus, 5000);
      
      return () => clearInterval(interval);
    }
  }, [activeRepo, repoStatus.ready]);

  const handleSubmitRepo = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!repoUrl) return;
    
    setLoading(true);
    setError("");
    
    try {
      const response = await loadRepository(repoUrl);
      
      if (response.success) {
        setActiveRepo(repoUrl);
        setRepoStatus({ loaded: true, ready: false });
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
        <form onSubmit={handleSubmitRepo} className="flex flex-col md:flex-row gap-4">
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            placeholder="Enter GitHub repository URL (e.g., https://github.com/username/repo)"
            className="flex-grow p-3 border rounded-lg"
            disabled={loading || repoStatus.ready}
          />
          <button
            type="submit"
            className="bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
            disabled={loading || !repoUrl || repoStatus.ready}
          >
            {loading && !repoStatus.ready ? "Loading..." : "Load Repository"}
          </button>
        </form>
      </section>

      {/* Repository Status */}
      {activeRepo && (
        <section className="mb-8 p-4 border rounded-lg bg-gray-50">
          <div className="flex items-center justify-between">
            <div>
              <h2 className="text-lg font-semibold">Repository: {activeRepo}</h2>
              <p className="text-sm text-gray-600">
                Status: {repoStatus.ready ? "Ready" : repoStatus.loaded ? "Loading..." : "Not loaded"}
              </p>
            </div>
            {repoStatus.ready && (
              <div className="flex gap-2">
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
              </div>
            )}
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
              <form onSubmit={handleSubmitQuery} className="mb-4">
                <div className="flex flex-col gap-4">
                  <textarea
                    value={query}
                    onChange={(e) => setQuery(e.target.value)}
                    placeholder="Ask a question about the repository..."
                    className="w-full p-3 border rounded-lg h-32"
                    disabled={loading}
                  />
                  <button
                    type="submit"
                    className="bg-blue-600 text-white p-3 rounded-lg hover:bg-blue-700 transition-colors disabled:bg-gray-400"
                    disabled={loading || !query}
                  >
                    {loading ? "Thinking..." : "Ask Question"}
                  </button>
                </div>
              </form>

              {answer && (
                <div className="p-4 bg-gray-50 border rounded-lg">
                  <h3 className="font-semibold text-lg mb-2">Answer:</h3>
                  <div className="prose max-w-none">
                    {answer.split("\n").map((line, i) => (
                      <p key={i}>{line}</p>
                    ))}
                  </div>
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
