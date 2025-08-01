"use client";

import { useState, useEffect } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import Button from "@/components/Button";
import Select from "@/components/Select";

export default function EvalJobDetailPage() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const evalJobId = searchParams.get("eval_job_id");
  
  const [metrics, setMetrics] = useState([]);
  const [loading, setLoading] = useState(false);
  const [page, setPage] = useState(1);
  const [totalMetrics, setTotalMetrics] = useState(0);
  const [expandedMetric, setExpandedMetric] = useState({});
  const [refreshInterval, setRefreshInterval] = useState("1min");
  const [lastActivity, setLastActivity] = useState(Date.now());
  const [overallMetrics, setOverallMetrics] = useState(null);
  const [showOverallMetrics, setShowOverallMetrics] = useState(false);
  
  const pageSize = 50;

  // Fetch eval metrics
  const fetchMetrics = async () => {
    if (!evalJobId) return;
    
    setLoading(true);
    try {
      const response = await fetch(
        "http://localhost:8000/chain/samples/github-rag/eval/metrics",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            eval_job_id: evalJobId,
            page,
            page_size: pageSize,
          }),
        }
      );
      const data = await response.json();
      if (data.success === "ok") {
        setMetrics(data.metrics);
        setTotalMetrics(data.total_metrics);
      }
    } catch (error) {
      console.error("Error fetching metrics:", error);
    }
    setLoading(false);
  };

  // Fetch overall metrics
  const fetchOverallMetrics = async () => {
    if (!evalJobId) return;
    
    try {
      const response = await fetch(
        "http://localhost:8000/chain/samples/github-rag/eval/overall-metrics",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            eval_job_id: evalJobId,
          }),
        }
      );
      const data = await response.json();
      if (data.success === "ok") {
        setOverallMetrics(data.overall_metrics);
      }
    } catch (error) {
      console.error("Error fetching overall metrics:", error);
    }
  };

  useEffect(() => {
    fetchMetrics();
    fetchOverallMetrics();
  }, [evalJobId, page]);

  // Auto-refresh setup
  useEffect(() => {
    const intervals = {
      "1min": 60000,
      "5min": 300000,
    };

    const intervalId = setInterval(() => {
      const timeSinceActivity = Date.now() - lastActivity;
      if (timeSinceActivity < 3600000) {
        fetchMetrics();
        fetchOverallMetrics();
      }
    }, intervals[refreshInterval]);

    return () => clearInterval(intervalId);
  }, [refreshInterval, lastActivity, evalJobId, page]);

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

  const toggleExpanded = (metricId) => {
    setExpandedMetric(prev => ({
      ...prev,
      [metricId]: !prev[metricId]
    }));
  };

  const getMetricBadge = (score, passed) => {
    const color = passed ? "bg-green-100 text-green-800" : "bg-red-100 text-red-800";
    return (
      <span className={`px-2 py-1 rounded text-xs ${color}`}>
        {(score * 100).toFixed(1)}% {passed ? "✓" : "✗"}
      </span>
    );
  };

  const totalPages = Math.ceil(totalMetrics / pageSize);

  const metricDisplayNames = {
    g_eval_correctness: "Correctness",
    g_eval_coherence: "Coherence",
    g_eval_tonality: "Tonality",
    g_eval_safety: "Safety",
    dag_score: "DAG Score",
    contextual_relevancy: "Context Relevancy",
    contextual_precision: "Context Precision",
    contextual_recall: "Context Recall",
    answer_relevancy: "Answer Relevancy",
    answer_faithfulness: "Answer Faithfulness"
  };

  return (
    <div className="max-w-7xl">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-3xl font-bold mb-1">Evaluation Details</h1>
          <p className="text-gray-600">
            Eval Job ID: {evalJobId}
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
            onClick={() => setShowOverallMetrics(!showOverallMetrics)}
            variant="secondary"
          >
            {showOverallMetrics ? "Hide" : "Show"} Overall Metrics
          </Button>
          <Button
            onClick={() => router.back()}
            variant="secondary"
          >
            Back to Evaluations
          </Button>
        </div>
      </div>

      {/* Overall Metrics Summary */}
      {showOverallMetrics && overallMetrics && (
        <div className="bg-white shadow rounded-lg p-6 mb-6">
          <h2 className="text-xl font-bold mb-4">Overall Metrics Summary</h2>
          <p className="text-gray-600 mb-4">
            Total Evaluated: {overallMetrics.total_evaluated} Q&A pairs
          </p>
          
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {Object.entries(overallMetrics.metrics_summary).map(([metric, data]) => (
              <div key={metric} className="bg-gray-50 rounded p-4">
                <h3 className="font-semibold text-sm mb-2">
                  {metricDisplayNames[metric] || metric}
                </h3>
                <div className="space-y-1 text-sm">
                  <div className="flex justify-between">
                    <span className="text-gray-600">Average:</span>
                    <span className="font-medium">
                      {(data.average_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Pass Rate:</span>
                    <span className="font-medium">
                      {(data.pass_rate * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="flex justify-between">
                    <span className="text-gray-600">Range:</span>
                    <span className="font-medium">
                      {(data.min_score * 100).toFixed(1)}% - {(data.max_score * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="text-xs text-gray-500 mt-1">
                    {data.total_passed}/{data.total_evaluated} passed
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {loading && metrics.length === 0 ? (
        <div className="text-center py-8">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-gray-900 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading evaluation metrics...</p>
        </div>
      ) : metrics.length === 0 ? (
        <div className="bg-gray-50 rounded-lg p-8 text-center">
          <p className="text-gray-600">
            No metrics available yet. The evaluation might still be processing.
          </p>
        </div>
      ) : (
        <>
          <div className="space-y-4">
            {metrics.map((metric) => (
              <div
                key={metric.id}
                className="bg-white shadow rounded-lg p-6"
              >
                <div className="flex justify-between items-start mb-4">
                  <div className="flex-1">
                    <h3 className="text-lg font-semibold text-gray-900 mb-2">
                      Question
                    </h3>
                    <p className="text-gray-700">{metric.question}</p>
                  </div>
                  <Button
                    onClick={() => toggleExpanded(metric.id)}
                    variant="ghost"
                    size="sm"
                  >
                    {expandedMetric[metric.id] ? "Collapse" : "Expand"}
                  </Button>
                </div>

                {/* Metrics Summary */}
                <div className="mt-4 flex flex-wrap gap-2">
                  {metric.metrics && Object.entries(metric.metrics).map(([key, value]) => {
                    if (key === "status") return null;
                    return (
                      <div key={key} title={value.reason}>
                        {getMetricBadge(value.score, value.passed)}
                        <span className="ml-1 text-xs text-gray-600">
                          {metricDisplayNames[key] || key}
                        </span>
                      </div>
                    );
                  })}
                </div>

                {expandedMetric[metric.id] && (
                  <div className="mt-6 space-y-4">
                    {/* Expected vs Actual Answer */}
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      <div>
                        <h4 className="text-md font-semibold text-gray-900 mb-2">
                          Expected Answer
                        </h4>
                        <div className="text-gray-700 whitespace-pre-wrap bg-gray-50 p-4 rounded">
                          {metric.expected_answer}
                        </div>
                      </div>
                      <div>
                        <h4 className="text-md font-semibold text-gray-900 mb-2">
                          Actual Answer
                        </h4>
                        <div className="text-gray-700 whitespace-pre-wrap bg-blue-50 p-4 rounded">
                          {metric.actual_answer}
                        </div>
                      </div>
                    </div>

                    {/* Detailed Metrics */}
                    <div>
                      <h4 className="text-md font-semibold text-gray-900 mb-2">
                        Detailed Metrics
                      </h4>
                      <div className="space-y-2">
                        {metric.metrics && Object.entries(metric.metrics).map(([key, value]) => {
                          if (key === "status") return null;
                          return (
                            <div key={key} className="bg-gray-50 p-3 rounded">
                              <div className="flex items-center justify-between mb-1">
                                <span className="font-medium text-sm">
                                  {metricDisplayNames[key] || key}
                                </span>
                                {getMetricBadge(value.score, value.passed)}
                              </div>
                              <p className="text-sm text-gray-600">
                                {value.reason}
                              </p>
                            </div>
                          );
                        })}
                      </div>
                    </div>

                    {/* Retrieved Chunks */}
                    {metric.relevant_chunks && metric.relevant_chunks.length > 0 && (
                      <div>
                        <h4 className="text-md font-semibold text-gray-900 mb-2">
                          Retrieved Chunks ({metric.relevant_chunks.length})
                        </h4>
                        <div className="space-y-2">
                          {metric.relevant_chunks.map((chunk, idx) => (
                            <div key={idx} className="bg-gray-100 p-3 rounded text-sm">
                              <div className="flex justify-between items-start mb-1">
                                <span className="font-medium text-xs text-gray-500">
                                  {chunk.file_path}
                                </span>
                                <span className="text-xs text-gray-500">
                                  Score: {chunk.score?.toFixed(3)}
                                </span>
                              </div>
                              <div className="text-gray-700 whitespace-pre-wrap">
                                {chunk.chunk_text}
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <div className="text-sm text-gray-500">
                      Q&A ID: {metric.qa_id} | File ID: {metric.file_id}
                    </div>
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