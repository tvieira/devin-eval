import httpx
from app.config import config


class GitHubClient:
    def __init__(self):
        self.token = config.GITHUB_TOKEN
        self.headers = {
            "Authorization": f"token {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }

    def post_comment(self, repo_owner: str, repo_name: str, issue_number: int, comment: str):
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/comments"
        response = httpx.post(url, headers=self.headers, json={"body": comment}, timeout=30.0)
        response.raise_for_status()

    def add_label(self, repo_owner: str, repo_name: str, issue_number: int, label: str):
        url = f"https://api.github.com/repos/{repo_owner}/{repo_name}/issues/{issue_number}/labels"
        response = httpx.post(url, headers=self.headers, json=[label], timeout=30.0)
        response.raise_for_status()

    def post_completion_comment(self, repo_owner: str, repo_name: str, issue_number: int, 
                                devin_session_url: str, pr_url: str, summary: str):
        comment = f"""Automation completed.

Devin Session: {devin_session_url}

Pull Request: {pr_url}

Summary:
{summary}
"""
        self.post_comment(repo_owner, repo_name, issue_number, comment)
        self.add_label(repo_owner, repo_name, issue_number, "automation-complete")
