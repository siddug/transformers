# All the github related utils
import base64
import requests
import os

# Get the github token from the environment variable
GITHUB_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN")

def get_repo_files(repo_name: str, repo_owner: str, repo_branch: str = "main") -> list[str]:
    """
    Get the files and folders in the repo

    Do get request to GET https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1
    """

    print(f"GITHUB_TOKEN: {GITHUB_TOKEN}")

    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/git/trees/{repo_branch}?recursive=1"
    response = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    response.raise_for_status()
    return response.json()["tree"]

def get_repo_file_raw(repo_name: str, repo_owner: str, file_path: str, repo_branch: str = "main") -> str:
    """
    Get the raw content of a file in the repo

    Do get request to GET https://api.github.com/repos/{owner}/{repo}/contents/{path}
    """
    url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/contents/{file_path}?ref={repo_branch}"
    response = requests.get(url, headers={"Authorization": f"token {GITHUB_TOKEN}"})
    response.raise_for_status()
    json_data = response.json()
    
    # If it's a list, it means the path is a directory
    if isinstance(json_data, list):
        raise ValueError(f"Path '{file_path}' is a directory, not a file")
    
    # If it's a file but doesn't have content (e.g., too large), skip it
    if "content" not in json_data:
        raise ValueError(f"File '{file_path}' content not available (file may be too large)")
    
    return base64.b64decode(json_data["content"]).decode("utf-8")
