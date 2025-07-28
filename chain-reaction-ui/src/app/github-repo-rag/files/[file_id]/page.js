'use client';

import { useState, useEffect } from 'react';
import { useParams, useRouter } from 'next/navigation';
import Button from '@/components/Button';

export default function GithubRepoRAGFilePage({ params }) {
    const router = useRouter();
    const { file_id } = params;
    const [file, setFile] = useState(null);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchFile = async () => {
            setLoading(true);
            const response = await fetch(`http://localhost:8000/chain/samples/github-rag/files/${file_id}`);
            const data = await response.json();
            setFile(data.file);
            setLoading(false);
        };
        fetchFile();
    }, [file_id]);

    if (loading) {
        return (
            <div className="max-w-6xl">
                <div className="flex justify-center py-8">
                    <div className="text-gray-500">Loading file details...</div>
                </div>
            </div>
        );
    }

    if (!file) {
        return (
            <div className="max-w-6xl">
                <div className="text-center py-8 text-gray-500">
                    File not found.
                </div>
            </div>
        );
    }

    return (
        <div className="max-w-6xl">
            <div className="mb-4">
                <Button 
                    size="small" 
                    variant="secondary"
                    onClick={() => router.back()}
                >
                    ← Back to Files
                </Button>
            </div>
            
            <h1 className="text-3xl font-bold mb-1">File Details</h1>
            <p className="text-gray-600 mb-8">{file.path}</p>

            <div className="space-y-8">
                <div className="bg-white rounded-lg shadow p-6">
                    <h2 className="text-xl font-bold mb-4">File Information</h2>
                    <dl className="grid grid-cols-1 gap-x-4 gap-y-6 sm:grid-cols-2">
                        <div>
                            <dt className="text-sm font-medium text-gray-500">Path</dt>
                            <dd className="mt-1 text-sm text-gray-900">{file.path}</dd>
                        </div>
                        <div>
                            <dt className="text-sm font-medium text-gray-500">Added At</dt>
                            <dd className="mt-1 text-sm text-gray-900">
                                {new Date(file.added_at).toLocaleString()}
                            </dd>
                        </div>
                        <div>
                            <dt className="text-sm font-medium text-gray-500">Summary Status</dt>
                            <dd className="mt-1">
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
                            </dd>
                        </div>
                        <div>
                            <dt className="text-sm font-medium text-gray-500">Chunks Status</dt>
                            <dd className="mt-1">
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
                            </dd>
                        </div>
                    </dl>
                </div>

                {file.summary && (
                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-xl font-bold mb-4">File Summary</h2>
                        <p className="text-gray-700 whitespace-pre-wrap">{file.summary}</p>
                    </div>
                )}

                {file.raw_content && (
                    <div className="bg-white rounded-lg shadow p-6">
                        <h2 className="text-xl font-bold mb-4">File Content</h2>
                        <pre className="bg-gray-50 p-4 rounded overflow-x-auto">
                            <code className="text-sm">{file.raw_content}</code>
                        </pre>
                    </div>
                )}
            </div>
        </div>
    );
}