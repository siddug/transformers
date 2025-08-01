"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Button from "@/components/Button";
import Select from "@/components/Select";

export default function QABatchDetailPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const batchId = searchParams.get("batch_id");
  
  const [qaPairs, setQaPairs] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalPairs, setTotalPairs] = useState(0);
  const [expandedQA, setExpandedQA] = useState({});
  const [refreshInterval, setRefreshInterval] = useState("1min");
  const [lastActivity, setLastActivity] = useState(Date.now());
  const [archivingQA, setArchivingQA] = useState(null);
  
  const pageSize = 50;

  // Fetch Q&A pairs
  const fetchQAPairs = async () => {
    if (!batchId) return;
    
    setLoading(true);
    try {
      const response = await fetch(
        "http://localhost:8000/chain/samples/github-rag/qa/pairs",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            batch_id: batchId,
            page,
            page_size: pageSize,
          }),
        }
      );
      const data = await response.json();
      if (data.success === "ok") {
        setQaPairs(data.qa_pairs);
        setTotalPairs(data.total_pairs);
      }
    } catch (error) {
      console.error("Error fetching Q&A pairs:", error);
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchQAPairs();
  }, [batchId, page]);

  // Auto-refresh setup
  useEffect(() => {
    const intervals = {
      "1min": 60000,
      "5min": 300000,
    };

    const intervalId = setInterval(() => {
      const timeSinceActivity = Date.now() - lastActivity;
      if (timeSinceActivity < 3600000) {
        // 1 hour
        fetchQAPairs();
      }
    }, intervals[refreshInterval]);

    return () => clearInterval(intervalId);
  }, [refreshInterval, lastActivity, batchId, page]);

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

  const toggleExpanded = (qaId) => {
    setExpandedQA(prev => ({
      ...prev,
      [qaId]: !prev[qaId]
    }));
  };

  // Archive Q&A pair
  const archiveQAPair = async (qaId) => {
    if (!confirm("Are you sure you want to archive this Q&A pair? This action cannot be undone.")) {
      return;
    }
    
    setArchivingQA(qaId);
    try {
      const response = await fetch(
        "http://localhost:8000/chain/samples/github-rag/qa/pair/archive",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ qa_id: qaId }),
        }
      );
      const data = await response.json();
      if (data.success === "ok") {
        // Refresh Q&A pairs list
        fetchQAPairs();
      } else {
        alert("Failed to archive Q&A pair");
      }
    } catch (error) {
      console.error("Error archiving Q&A pair:", error);
      alert("Failed to archive Q&A pair");
    }
    setArchivingQA(null);
  };

  const getStrategyBadge = (strategy) => {
    if (!strategy) return null;
    
    const strategies = strategy.split("+");
    return (
      <div className="flex gap-1 flex-wrap">
        {strategies.map((s, idx) => (
          <span
            key={idx}
            className="px-2 py-1 bg-purple-100 text-purple-800 rounded text-xs"
          >
            {s}
          </span>
        ))}
      </div>
    );
  };

  const totalPages = Math.ceil(totalPairs / pageSize);

  return (
    <div className="max-w-6xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-1">Q&A Batch Details</h1>
          <p className="text-gray-600">
            Batch ID: {batchId}
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
            onClick={() => router.back()}
            variant="secondary"
          >
            Back to Batches
          </Button>
        </div>
      </div>

      {loading && qaPairs.length === 0 ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading Q&A pairs...</p>
        </div>
      ) : qaPairs.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-600">
            No Q&A pairs generated yet. The batch might still be processing.
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {qaPairs.map((qa) => (
              <div
                key={qa.id}
                className="bg-white shadow rounded-lg p-6"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Question
                    </h3>
                    <p className="text-gray-700">{qa.question}</p>
                  </div>
                  <div className="flex gap-2">
                    <Button
                      onClick={() => archiveQAPair(qa.id)}
                      variant="secondary"
                      size="sm"
                      disabled={archivingQA === qa.id}
                    >
                      {archivingQA === qa.id ? "Archiving..." : "Archive"}
                    </Button>
                    <Button
                      onClick={() => toggleExpanded(qa.id)}
                      variant="ghost"
                      size="sm"
                    >
                      {expandedQA[qa.id] ? "Collapse" : "Expand"}
                    </Button>
                  </div>
                </div>

                {expandedQA[qa.id] && (
                  <div className="mt-4 space-y-4">
                    <div>
                      <h4 className="text-md font-semibold text-gray-900 mb-2">
                        Answer
                      </h4>
                      <div className="text-gray-700 whitespace-pre-wrap bg-gray-50 p-4 rounded">
                        {qa.answer}
                      </div>
                    </div>

                    <div className="flex gap-6 text-sm">
                      <div>
                        <span className="text-gray-500">Evolution Strategy:</span>
                        <div className="mt-1">
                          {getStrategyBadge(qa.evolution_strategy)}
                        </div>
                      </div>
                      <div>
                        <span className="text-gray-500">Question Score:</span>
                        <span className="ml-2 font-medium">
                          {qa.question_score?.toFixed(2) || "N/A"}
                        </span>
                      </div>
                      <div>
                        <span className="text-gray-500">Chunk Score:</span>
                        <span className="ml-2 font-medium">
                          {qa.chunk_score?.toFixed(2) || "N/A"}
                        </span>
                      </div>
                    </div>

                    <div className="text-sm text-gray-500">
                      File ID: {qa.file_id} | Chunk ID: {qa.chunk_id}
                    </div>

                    {qa.flow_logs && (
                      <div className="mt-4">
                        <h4 className="text-md font-semibold text-gray-900 mb-2">
                          Flow Logs
                        </h4>
                        <div className="bg-gray-100 p-4 rounded text-xs font-mono overflow-auto max-h-96">
                          <div className="space-y-2">
                            <div>
                              <strong>Chunk Text:</strong>
                              <div className="mt-1 text-gray-700">{qa.flow_logs.chunk_text}</div>
                            </div>
                            
                            <div>
                              <strong>Original Question:</strong>
                              <div className="mt-1 text-gray-700">{qa.flow_logs.original_question}</div>
                            </div>
                            
                            <div>
                              <strong>Chunk Scores:</strong>
                              <div className="mt-1">
                                {qa.flow_logs.scores && Object.entries(qa.flow_logs.scores).map(([key, value]) => (
                                  <div key={key} className="text-gray-700">
                                    {key}: {typeof value === 'number' ? value.toFixed(2) : value}
                                  </div>
                                ))}
                              </div>
                            </div>
                            
                            <div>
                              <strong>Timing:</strong>
                              <div className="mt-1">
                                {qa.flow_logs.timing && Object.entries(qa.flow_logs.timing).map(([block, times]) => (
                                  <div key={block} className="text-gray-700">
                                    {block}: {times.total_ms}ms
                                  </div>
                                ))}
                              </div>
                            </div>
                            
                            <details className="mt-2">
                              <summary className="cursor-pointer text-blue-600 hover:text-blue-800">
                                View Detailed Logs ({qa.flow_logs.logs?.length || 0} entries)
                              </summary>
                              <div className="mt-2 space-y-1">
                                {qa.flow_logs.logs?.map((log, idx) => (
                                  <div key={idx} className="text-gray-600 text-xs">
                                    <span className="text-gray-500">{new Date(log.timestamp).toLocaleTimeString()}</span>
                                    {' '}
                                    <span className="font-medium">[{log.block}]</span>
                                    {' '}
                                    <span>{log.message}</span>
                                  </div>
                                ))}
                              </div>
                            </details>
                          </div>
                        </div>
                      </div>
                    )}
                  </div>
                )}
              </div>
            ))}
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
            Data might be stale. Refresh has been paused due to inactivity. Click anywhere to resume auto-refresh.
          </p>
        </div>
      )}
    </div>
  );
}