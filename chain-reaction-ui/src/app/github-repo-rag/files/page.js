"use client";

import { useState, useEffect } from "react";
import { useSearchParams } from "next/navigation";
import Select from "@/components/Select";
import Button from "@/components/Button";

export default function GithubRepoRAGFilesPage() {
  const searchParams = useSearchParams();
  const repoId = searchParams.get('repo_id');
  const [loading, setLoading] = useState(false);
  const [files, setFiles] = useState([]);
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(100);
  const [totalNumFiles, setTotalNumFiles] = useState(0);

  useEffect(() => {
    const fetchFiles = async () => {
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
    fetchFiles();
  }, [repoId, page, pageSize]);

  return (
    <div className="max-w-7xl">
      <h1 className="text-3xl font-bold mb-1">Github RAG Files</h1>
      <p className="text-gray-600 mb-8">View the files in the repo</p>

      <div className="space-y-6">
        <div>
          <h2 className="text-xl font-bold mb-4">Files</h2>
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
        </div>
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
    </div>
  );
}
