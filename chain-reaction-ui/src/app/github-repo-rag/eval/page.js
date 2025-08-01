"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Button from "@/components/Button";
import Select from "@/components/Select";

export default function EvalPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const repoId = searchParams.get("repo_id");
  
  const [evalJobs, setEvalJobs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [creatingEval, setCreatingEval] = useState(false);
  const [page, setPage] = useState(1);
  const [totalJobs, setTotalJobs] = useState(0);
  const [refreshInterval, setRefreshInterval] = useState("1min");
  const [lastActivity, setLastActivity] = useState(Date.now());
  const [qaBatches, setQaBatches] = useState([]);
  const [selectedBatchId, setSelectedBatchId] = useState("");
  const [showCreateModal, setShowCreateModal] = useState(false);
  
  const pageSize = 20;

  // Fetch eval jobs
  const fetchEvalJobs = async () => {
    if (!repoId) return;
    
    setLoading(true);
    try {
      const response = await fetch(
        "http://localhost:8000/chain/samples/github-rag/eval/jobs",
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
        setEvalJobs(data.eval_jobs);
        setTotalJobs(data.total_jobs);
      }
    } catch (error) {
      console.error("Error fetching eval jobs:", error);
    }
    setLoading(false);
  };

  // Fetch QA batches for dropdown
  const fetchQABatches = async () => {
    if (!repoId) return;
    
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
            page: 1,
            page_size: 100,
          }),
        }
      );
      const data = await response.json();
      if (data.success === "ok") {
        setQaBatches(data.batches.filter(b => b.status === "completed" || b.status === "running"));
      }
    } catch (error) {
      console.error("Error fetching QA batches:", error);
    }
  };

  // Create new eval job
  const createNewEval = async () => {
    if (!selectedBatchId) {
      alert("Please select a Q&A batch");
      return;
    }
    
    setCreatingEval(true);
    try {
      const response = await fetch(
        "http://localhost:8000/chain/samples/github-rag/eval/create",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ 
            qa_batch_id: selectedBatchId,
            repo_id: repoId 
          }),
        }
      );
      const data = await response.json();
      if (data.success === "ok") {
        setShowCreateModal(false);
        setSelectedBatchId("");
        fetchEvalJobs();
      } else if (response.status === 400) {
        alert(data.detail || "Failed to create eval job");
      }
    } catch (error) {
      console.error("Error creating eval job:", error);
      alert("Failed to create eval job");
    }
    setCreatingEval(false);
  };

  // Auto-refresh setup
  useEffect(() => {
    fetchEvalJobs();
  }, [repoId, page]);

  useEffect(() => {
    if (showCreateModal) {
      fetchQABatches();
    }
  }, [showCreateModal]);

  useEffect(() => {
    const intervals = {
      "1min": 60000,
      "5min": 300000,
    };

    const intervalId = setInterval(() => {
      const timeSinceActivity = Date.now() - lastActivity;
      if (timeSinceActivity < 3600000) {
        fetchEvalJobs();
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

  const totalPages = Math.ceil(totalJobs / pageSize);

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
            onClick={() => window.location.href = `/github-repo-rag/qa-generation?repo_id=${repoId}`}
            className="py-2 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 font-medium text-sm"
          >
            Q&A Generation
          </button>
          <button
            className="py-2 px-1 border-b-2 border-gray-900 text-gray-900 font-medium text-sm"
          >
            Evaluation
          </button>
        </nav>
      </div>

      <div className="max-w-6xl">
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold mb-1">Evaluations</h2>
            <p className="text-gray-600">
              Evaluate the quality of generated Q&A pairs
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
              onClick={() => setShowCreateModal(true)}
              variant="primary"
            >
              Create New Evaluation
            </Button>
          </div>
        </div>

        {loading && evalJobs.length === 0 ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
            <p className="mt-4 text-gray-600">Loading evaluations...</p>
          </div>
        ) : evalJobs.length === 0 ? (
          <div className="bg-gray-50 rounded-lg p-8 text-center">
            <p className="text-gray-600 mb-4">
              No evaluations created yet. Create your first evaluation to assess Q&A quality.
            </p>
          </div>
        ) : (
          <>
            <div className="bg-white shadow overflow-hidden sm:rounded-md">
              <ul className="divide-y divide-gray-200">
                {evalJobs.map((job) => (
                  <li key={job.id}>
                    <div
                      className="px-4 py-4 hover:bg-gray-50 cursor-pointer"
                      onClick={() =>
                        router.push(
                          `/github-repo-rag/eval/job?eval_job_id=${job.id}`
                        )
                      }
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex-1">
                          <div className="flex items-center">
                            <p className="text-sm font-medium text-gray-900">
                              Eval ID: {job.id}
                            </p>
                            <div className="ml-4">
                              {getStatusBadge(job.status)}
                            </div>
                          </div>
                          <div className="mt-2 flex items-center text-sm text-gray-500">
                            <span>
                              Progress: {job.processed_qa_pairs} / {job.total_qa_pairs} Q&A pairs
                            </span>
                            <span className="mx-2">•</span>
                            <span>
                              Q&A Batch: {job.qa_batch_id.slice(0, 8)}...
                            </span>
                            <span className="mx-2">•</span>
                            <span>
                              Created: {new Date(job.created_at).toLocaleString()}
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
              Data might be stale. Click anywhere to resume auto-refresh.
            </p>
          </div>
        )}
      </div>

      {/* Create Eval Modal */}
      {showCreateModal && (
        <div className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center p-4 z-50">
          <div className="bg-white rounded-lg max-w-md w-full p-6">
            <h3 className="text-lg font-medium text-gray-900 mb-4">
              Create New Evaluation
            </h3>
            <div className="mb-4">
              <label className="block text-sm font-medium text-gray-700 mb-2">
                Select Q&A Batch
              </label>
              <select
                value={selectedBatchId}
                onChange={(e) => setSelectedBatchId(e.target.value)}
                className="w-full p-2 border border-gray-300 rounded-md"
              >
                <option value="">Select a batch...</option>
                {qaBatches.map((batch) => (
                  <option key={batch.id} value={batch.id}>
                    Batch {batch.id.slice(0, 8)}... - {batch.processed_files} files - Created {new Date(batch.added_at).toLocaleDateString()}
                  </option>
                ))}
              </select>
              {qaBatches.length === 0 && (
                <p className="mt-2 text-sm text-gray-500">
                  No completed Q&A batches available. Please create and complete a Q&A batch first.
                </p>
              )}
            </div>
            <div className="flex justify-end gap-3">
              <Button
                onClick={() => {
                  setShowCreateModal(false);
                  setSelectedBatchId("");
                }}
                variant="secondary"
              >
                Cancel
              </Button>
              <Button
                onClick={createNewEval}
                disabled={!selectedBatchId || creatingEval}
                variant="primary"
              >
                {creatingEval ? "Creating..." : "Create Evaluation"}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}