"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import Select from "@/components/Select";
import Button from "@/components/Button";

/*
Repo Ingestion page:
1. User sees a single input field with submit button. + list of some popular repos that they can click on. Clicking on them is equivalent to submitting the input field with the repo url.
2. Show a loading state on the button when the user clicks on it until the repo is ingested.
3. If user clicked on a popular repo, then the input field is pre-filled with the repo url and rest of UX remains the same.
4. Call the /chain/samples/github-rag endpoint with the repo url. get the repo id and navigate to /chain/samples/github-repo-rag/files?repo_id={repo_id}
5. Nitty gritties: User might enter the enter repo url, the job of converting it to owner, repo etc is handled by the backend.

Repo Files page
1. Get the repo id from the url 
2. Call the /chain/samples/github-rag/files endpoint with the repo id, page and page size.
3. Show the files in a table.
4. Render the files in a table with all the columns.
5. Render the pagination buttons for user to navigate through the files.
6. Show a loading state on the page until the files are fetched for the first time.
7. There should be a default loader on the top right with dropdown set to 1min (user can change to 5min). 
8. based on the the time, in a loop, call the /chain/samples/github-rag/files endpoint with the repo id, page and page size to refresh the results
9. Maintain session activity as a time variable. Whenever user interacts with the page, reset the time variable.
10. Detach the loop subscriber if time is > 1hr. 
11. Show a fixed loader after 1hr that the data might be stale and they can refresh the page to get the latest data.
12. Clicking on the file path should navigate to the /chain/samples/github-repo-rag/files/{file_id} page.

Repo File page
1. Get the file id from the url
2. Call the /chain/samples/github-repo-rag/files/{file_id} endpoint to get the file details.
3. Show the file details in a table.
4. Show a loading state on the page until the file details are fetched.
5. Show the file details in a table.
6. Similar to the Repo Files page, there should be a default loader on the top right with dropdown set to 1min (user can change to 5min). 
7. based on the the time, in a loop, call the /chain/samples/github-repo-rag/files/{file_id} endpoint with the repo id, page and page size to refresh the results
8. Maintain session activity as a time variable. Whenever user interacts with the page, reset the time variable.
9. Detach the loop subscriber if time is > 1hr. 
10. Show a fixed loader after 1hr that the data might be stale and they can refresh the page to get the latest data.
11. Clicking on the file path should navigate to the /chain/samples/github-repo-rag/files/{file_id} page.
*/

export default function GithubRepoRAGPage() {
  const router = useRouter();
  const [repoUrl, setRepoUrl] = useState("");
  const [repoId, setRepoId] = useState(null);
  const [loading, setLoading] = useState(false);

  const popularRepos = [
    {
      name: "browserable/browserable",
      url: "https://github.com/browserable/browserable",
    },
    { name: "facebook/react", url: "https://github.com/facebook/react" },
    { name: "vercel/next.js", url: "https://github.com/vercel/next.js" },
    { name: "microsoft/vscode", url: "https://github.com/microsoft/vscode" },
    { name: "nodejs/node", url: "https://github.com/nodejs/node" },
    {
      name: "kubernetes/kubernetes",
      url: "https://github.com/kubernetes/kubernetes",
    },
  ];

  const handleRepoIngest = async () => {
    setLoading(true);
    const response = await fetch(
      "http://localhost:8000/chain/samples/github-rag",
      {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({ repo_url: repoUrl }),
      }
    );
    const data = await response.json();
    if (data.success !== "ok") {
      alert("Failed to ingest repo");
      setLoading(false);
      return;
    }
    setRepoId(data.repo_id);
    setLoading(false);
    router.push(`/github-repo-rag/files?repo_id=${data.repo_id}`);
  };

  return (
    <div className="max-w-4xl">
      <h1 className="text-3xl font-bold mb-1">Github RAG</h1>
      <p className="text-gray-600 mb-8">
        Ingest a Github repo and view the files
      </p>

      <div className="space-y-6">
        <div>
          <label className="block text-sm font-medium text-gray-700 mb-2">
            Github Repo URL
          </label>
          <input
            type="text"
            value={repoUrl}
            onChange={(e) => setRepoUrl(e.target.value)}
            className="w-full p-2 border border-gray-300 rounded-md"
          />
        </div>
        <Button
          size="small"
          onClick={handleRepoIngest}
          disabled={loading || !repoUrl}
        >
          {loading ? "Ingesting..." : "Ingest Repo"}
        </Button>

        <div className="mt-8">
          <h2 className="text-lg font-semibold mb-4">Popular Repositories</h2>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {popularRepos.map((repo) => (
              <Button
                key={repo.name}
                size="small"
                onClick={() => {
                  setRepoUrl(repo.url);
                }}
                variant="secondary"
                className="text-left justify-start"
              >
                {repo.name}
              </Button>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
