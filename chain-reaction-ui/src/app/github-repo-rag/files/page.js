"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Select from "@/components/Select";
import Button from "@/components/Button";
import ReactMarkdown from "react-markdown";

export default function GithubRepoRAGFilesPage() {
  const searchParams = useSearchParams();
  const repoId = searchParams.get('repo_id');
  const [activeTab, setActiveTab] = useState('files');
  
  // Files tab state
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);
  const [totalNumFiles, setTotalNumFiles] = useState(0);
  const [refreshInterval, setRefreshInterval] = useState("1min");
  const [lastActivity, setLastActivity] = useState(Date.now());
  
  // RAG tab state
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [ragLoading, setRagLoading] = useState(false);
  const [currentRequestId, setCurrentRequestId] = useState(null);

  const fetchFiles = async () => {
    if (!repoId) return;
    setLoading(true);
    const response = await fetch(
      `http://localhost:8000/chain/samples/github-rag/files`,
      {
        method: "POST",
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          repo_id: repoId,
          page: page,
          page_size: pageSize,
        }),
      }
    );
    const data = await response.json();
    setFiles(data.files);
    setTotalNumFiles(data.total_num_files);
    setLoading(false);
  };

  useEffect(() => {
    fetchFiles();
  }, [repoId, page, pageSize]);

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
        fetchFiles();
      }
    }, intervals[refreshInterval]);

    return () => clearInterval(intervalId);
  }, [refreshInterval, lastActivity, repoId, page, pageSize]);

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

  const handleAskQuestion = async () => {
    if (!question.trim()) return;
    
    setRagLoading(true);
    const newMessage = { role: 'user', content: question };
    const updatedMessages = [...messages, newMessage];
    setMessages(updatedMessages);
    
    try {
      // Create RAG request
      const response = await fetch(
        'http://localhost:8000/chain/samples/github-rag/request/create',
        {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            repo_id: repoId,
            messages: updatedMessages,
          }),
        }
      );
      const data = await response.json();
      
      if (data.success === 'ok') {
        setCurrentRequestId(data.request_id);
        setQuestion('');
        // Start polling for response
        pollForResponse(data.request_id);
      }
    } catch (error) {
      console.error('Error creating RAG request:', error);
      setRagLoading(false);
    }
  };

  const pollForResponse = async (requestId) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(
          'http://localhost:8000/chain/samples/github-rag/request/status',
          {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify({
              request_id: requestId,
            }),
          }
        );
        const data = await response.json();
        
        if (data.success === 'ok' && data.status) {
          // Check if the response is ready (status is 'success' and response_details exists)
          if (data.status.status === 'success' && data.status.response_details) {
            clearInterval(pollInterval);
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: data.status.response_details.response
            }]);
            setRagLoading(false);
            setCurrentRequestId(null);
          } else if (data.status.status === 'error') {
            clearInterval(pollInterval);
            setRagLoading(false);
            setCurrentRequestId(null);
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: data.status.response_details.response
            }]);
          }
        }
      } catch (error) {
        console.error('Error polling for response:', error);
        clearInterval(pollInterval);
        setRagLoading(false);
      }
    }, 2000); // Poll every 2 seconds
    
    // Stop polling after 2 minutes
    setTimeout(() => {
      clearInterval(pollInterval);
      if (ragLoading) {
        setRagLoading(false);
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: 'Request timed out. Please try again.'
        }]);
      }
    }, 120000);
  };

  return (
    <div className="max-w-7xl">
      <h1 className="text-3xl font-bold mb-1">Github RAG</h1>
      <p className="text-gray-600 mb-8">Explore repository files and ask questions</p>

      {/* Tabs */}
      <div className="border-b border-gray-200 mb-6">
        <nav className="-mb-px flex space-x-8">
          <button
            onClick={() => setActiveTab('files')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'files'
                ? 'border-gray-900 text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            Files
          </button>
          <button
            onClick={() => setActiveTab('rag')}
            className={`py-2 px-1 border-b-2 font-medium text-sm ${
              activeTab === 'rag'
                ? 'border-gray-900 text-gray-900'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            }`}
          >
            RAG
          </button>
          <button
            onClick={() => window.location.href = `/github-repo-rag/qa-generation?repo_id=${repoId}`}
            className="py-2 px-1 border-b-2 border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300 font-medium text-sm"
          >
            Q&A Generation
          </button>
        </nav>
      </div>

      {activeTab === 'files' ? (
        <div className="space-y-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold">Files</h2>
            <Select
              label="Auto-refresh"
              value={refreshInterval}
              onChange={(e) => setRefreshInterval(e.target.value)}
              options={[
                { value: "1min", label: "1 minute" },
                { value: "5min", label: "5 minutes" },
              ]}
            />
          </div>
          {loading ? (
            <div className="flex justify-center py-8">
              <div className="text-gray-500">Loading files...</div>
            </div>
          ) : files.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              No files found in this repository.
            </div>
          ) : (
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-gray-200">
              <thead className="bg-gray-50">
                <tr>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">File Name</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Summary Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Chunks Status</th>
                  <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">Added At</th>
                </tr>
              </thead>
              <tbody className="bg-white divide-y divide-gray-200">
                {files.map((file) => (
                  <tr key={file.id} className="hover:bg-gray-50">
                    <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                      <a
                        href={`/github-repo-rag/files/${file.id}`}
                        className="text-blue-600 hover:text-blue-900"
                      >
                        {file.path}
                      </a>
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {file.summary_status === "pending" ? (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                          Pending
                        </span>
                      ) : file.summary_status === "skipped" ? (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                          Skipped
                        </span>
                      ) : (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          Completed
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm">
                      {file.chunks_status === "pending" ? (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-yellow-100 text-yellow-800">
                          Pending
                        </span>
                      ) : file.chunks_status === "skipped" ? (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-gray-100 text-gray-800">
                          Skipped
                        </span>
                      ) : (
                        <span className="px-2 inline-flex text-xs leading-5 font-semibold rounded-full bg-green-100 text-green-800">
                          Completed
                        </span>
                      )}
                    </td>
                    <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                      {new Date(file.added_at).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          )}
          <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-sm text-gray-700">Show</span>
            <Select
              className="w-14"
              size="small"
              options={[
                { label: "10", value: 10 },
                { label: "20", value: 20 },
                { label: "50", value: 50 },
                { label: "100", value: 100 },
              ]}
              value={pageSize}
              onChange={(e) => setPageSize(e.value)}
            />
            <span className="text-sm text-gray-700">entries</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              size="small"
              onClick={() => setPage(page - 1)}
              disabled={page === 1}
            >
              Previous
            </Button>
            <span className="text-sm text-gray-700">
              Page {page} of {Math.ceil(totalNumFiles / pageSize)}
            </span>
            <Button
              size="small"
              onClick={() => setPage(page + 1)}
              disabled={page === Math.ceil(totalNumFiles / pageSize)}
            >
              Next
            </Button>
          </div>
        </div>
        </div>
      ) : (
        <div className="space-y-6">
          <div>
            <h2 className="text-xl font-bold mb-4">Ask Questions</h2>
            
            {/* Question Input */}
            <div className="flex gap-2 mb-6">
              <input
                type="text"
                value={question}
                onChange={(e) => setQuestion(e.target.value)}
                onKeyPress={(e) => e.key === 'Enter' && handleAskQuestion()}
                placeholder="Ask a question about this repository..."
                className="flex-1 p-2 border border-gray-300 rounded-md"
                disabled={ragLoading}
              />
              <Button
                size="small"
                onClick={handleAskQuestion}
                disabled={ragLoading || !question.trim()}
              >
                {ragLoading ? "Processing..." : "Ask"}
              </Button>
            </div>

            {/* Messages Display */}
            <div className="space-y-4">
              {messages.length === 0 ? (
                <div className="text-center py-8 text-gray-500">
                  No messages yet. Ask a question to get started.
                </div>
              ) : (
                messages.map((message, index) => (
                  <div
                    key={index}
                    className={`p-4 rounded-lg ${
                      message.role === 'user'
                        ? 'bg-blue-50 ml-12'
                        : 'bg-gray-50 mr-12'
                    }`}
                  >
                    <div className="font-semibold mb-1">
                      {message.role === 'user' ? 'You' : 'Assistant'}
                    </div>
                    <div className="prose prose-sm max-w-none">
                      <ReactMarkdown>{message.content}</ReactMarkdown>
                    </div>
                  </div>
                ))
              )}
              
              {/* Loading indicator */}
              {ragLoading && (
                <div className="flex items-center justify-center py-4">
                  <div className="text-gray-500">Processing your question...</div>
                </div>
              )}
            </div>
          </div>
        </div>
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
