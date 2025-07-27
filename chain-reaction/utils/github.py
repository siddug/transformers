# All the github related utils
import base64
import requests
import os

# Get the github token from the environment variable
GITHUB_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN")


def get_repo_files(repo_name: str, repo_owner: str, repo_branch: str = "main") -> list[str]:
    """
    Get the files and folders in the repo

    Do get request to GET https://api.github.com/repos/{owner}/{repo}/contents/{path}
    """

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{repo_branch}?recursive=true"
    response = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    response.raise_for_status()
    return response.json()

def get_repo_file_raw(repo_name: str, repo_owner: str, file_path: str, repo_branch: str = "main") -> str:
    """
    Get the raw content of a file in the repo

    Do get request to GET https://api.github.com/repos/{owner}/{repo}/contents/{path}
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}?ref={repo_branch}"
    response = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    response.raise_for_status()
    return base64.b64decode(response.json()["content"]).decode("utf-8")
