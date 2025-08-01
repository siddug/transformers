"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Button from "@/components/Button";
import Select from "@/components/Select";

export default function QAGenerationPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const repoId = searchParams.get("repo_id");
  const [activeTab, setActiveTab] = useState('qa-generation');
  
  const [batches, setBatches] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creatingBatch, setCreatingBatch] = useState(false);
  const [page, setPage] = useState(1);
  const [totalBatches, setTotalBatches] = useState(0);
  const [refreshInterval, setRefreshInterval] = useState("1min");
  const [lastActivity, setLastActivity] = useState(Date.now());
  
  const pageSize = 20;

  // Fetch batches
  const fetchBatches = async () => {
    if (!repoId) return;
    
    setLoading(true);
    try {
      const response = await fetch(
        "http://localhost:8000/chain/samples/github-rag/qa/batches",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            repo_id: repoId,
            page,
            page_size: pageSize,
          }),
        }
      );
      const data = await response.json();
      if (data.success === "ok") {
        setBatches(data.batches);
        setTotalBatches(data.total_batches);
      }
    } catch (error) {
      console.error("Error fetching batches:", error);
    }
    setLoading(false);
  };

  // Create new batch
  const createNewBatch = async () => {
    setCreatingBatch(true);
    try {
      const response = await fetch(
        "http://localhost:8000/chain/samples/github-rag/qa/batch/create",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ repo_id: repoId }),
        }
      );
      const data = await response.json();
      if (data.success === "ok") {
        // Refresh batches list
        fetchBatches();
      } else if (response.status === 400) {
        alert(data.detail || "Failed to create batch");
      }
    } catch (error) {
      console.error("Error creating batch:", error);
      alert("Failed to create batch");
    }
    setCreatingBatch(false);
  };

  // Auto-refresh setup
  useEffect(() => {
    fetchBatches();
  }, [repoId, page]);

  useEffect(() => {
    const intervals = {
      "1min": 60000,
      "5min": 300000,
    };

    const intervalId = setInterval(() => {
      const timeSinceActivity = Date.now() - lastActivity;
      if (timeSinceActivity < 3600000) {
        // 1 hour
        fetchBatches();
      }
    }, intervals[refreshInterval]);

    return () => clearInterval(intervalId);
  }, [refreshInterval, lastActivity, repoId, page]);

  // Track user activity
  useEffect(() => {
    const handleActivity = () => setLastActivity(Date.now());
    window.addEventListener("click", handleActivity);
    window.addEventListener("keydown", handleActivity);
    return () => {
      window.removeEventListener("click", handleActivity);
      window.removeEventListener("keydown", handleActivity);
    };
  }, []);

  const getStatusBadge = (status) => {
    const statusColors = {
      idle: "bg-gray-200 text-gray-800",
      running: "bg-blue-200 text-blue-800",
      completed: "bg-green-200 text-green-800",
      failed: "bg-red-200 text-red-800",
    };
    
    return (
      <span
        className={`px-2 py-1 rounded-full text-xs font-medium ${
          statusColors[status] || statusColors.idle
        }`}
      >
        {status}
      </span>
    );
  };

  const totalPages = Math.ceil(totalBatches / pageSize);

  return (
    <div className="max-w-7xl">
      <h1 className="text-3xl font-bold mb-1">Github RAG</h1>
      <p className="text-gray-600 mb-8">Explore repository files and ask questions</p>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => window.location.href = `/github-repo-rag/files?repo_id=${repoId}`}
            className="py-2 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 font-medium text-sm"
          >
            Files
          </button>
          <button
            onClick={() => window.location.href = `/github-repo-rag/files?repo_id=${repoId}`}
            className="py-2 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 font-medium text-sm"
          >
            RAG
          </button>
          <button
            className="py-2 px-1 border-b-2 border-gray-900 text-gray-900 font-medium text-sm"
          >
            Q&A Generation
          </button>
          <button
            onClick={() => window.location.href = `/github-repo-rag/eval?repo_id=${repoId}`}
            className="py-2 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 font-medium text-sm"
          >
            Evaluation
          </button>
        </nav>
      </div>

      <div className="max-w-6xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold mb-1">Q&A Generation</h2>
            <p className="text-gray-600">
              Generate synthetic Q&A pairs for repository
            </p>
          </div>
        <div className="flex items-center gap-4">
          <Select
            label="Auto-refresh"
            value={refreshInterval}
            onChange={(e) => setRefreshInterval(e.target.value)}
            options={[
              { value: "1min", label: "1 minute" },
              { value: "5min", label: "5 minutes" },
            ]}
          />
          <Button
            onClick={createNewBatch}
            disabled={creatingBatch}
            variant="primary"
          >
            {creatingBatch ? "Creating..." : "Create New Batch"}
          </Button>
        </div>
      </div>

      {loading && batches.length === 0 ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading batches...</p>
        </div>
      ) : batches.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-600 mb-4">
            No Q&A batches created yet. Create your first batch to generate synthetic Q&A pairs.
          </p>
        </div>
      ) : (
        <>
          <div className="bg-white shadow overflow-hidden sm:rounded-md">
            <ul className="divide-y divide-gray-200">
              {batches.map((batch) => (
                <li key={batch.id}>
                  <div
                    className="px-4 py-4 hover:bg-gray-50 cursor-pointer"
                    onClick={() =>
                      router.push(
                        `/github-repo-rag/qa-generation/batch?batch_id=${batch.id}`
                      )
                    }
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex-1">
                        <div className="flex items-center">
                          <p className="text-sm font-medium text-gray-900">
                            Batch ID: {batch.id}
                          </p>
                          <div className="ml-4">
                            {getStatusBadge(batch.status)}
                          </div>
                        </div>
                        <div className="mt-2 flex items-center text-sm text-gray-500">
                          <span>
                            Progress: {batch.processed_files} / {batch.total_files} files
                          </span>
                          <span className="mx-2">•</span>
                          <span>
                            Created: {new Date(batch.added_at).toLocaleString()}
                          </span>
                        </div>
                      </div>
                      <div className="ml-4">
                        <svg
                          className="h-5 w-5 text-gray-400"
                          fill="currentColor"
                          viewBox="0 0 20 20"
                        >
                          <path
                            fillRule="evenodd"
                            d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z"
                            clipRule="evenodd"
                          />
                        </svg>
                      </div>
                    </div>
                  </div>
                </li>
              ))}
            </ul>
          </div>

          {totalPages > 1 && (
            <div className="flex justify-center mt-6">
              <nav className="flex space-x-2">
                <Button
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page === 1}
                  variant="secondary"
                >
                  Previous
                </Button>
                <span className="px-4 py-2 text-gray-700">
                  Page {page} of {totalPages}
                </span>
                <Button
                  onClick={() => setPage(Math.min(totalPages, page + 1))}
                  disabled={page === totalPages}
                  variant="secondary"
                >
                  Next
                </Button>
              </nav>
            </div>
          )}
        </>
      )}

      {Date.now() - lastActivity > 3600000 && (
        <div className="mt-4 p-4 bg-yellow-50 border border-yellow-200 rounded-lg">
          <p className="text-sm text-yellow-800">
            Data might be stale. Click refresh to get the latest data.
          </p>
        </div>
      )}
      </div>
    </div>
  );
}