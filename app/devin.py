import httpx
import logging
from typing import Optional
from app.config import config
from app.models import DevinSessionRequest, DevinSessionResponse

logger = logging.getLogger(__name__)


class DevinClient:
    def __init__(self):
        self.service_user_token = config.DEVIN_SERVICE_USER_TOKEN
        self.org_id = config.DEVIN_ORG_ID
        # Remove 'org-' prefix if present to avoid duplication in URL
        if self.org_id.startswith('org-'):
            self.org_id = self.org_id[4:]
        self.base_url = "https://api.devin.ai/v3/organizations"
        self.headers = {
            "Authorization": f"Bearer {self.service_user_token}",
            "Content-Type": "application/json"
        }

    def create_session(self, request: DevinSessionRequest) -> DevinSessionResponse:
        prompt = self._build_prompt(request)
        
        payload = {
            "prompt": prompt,
            "repos": [request.repository_url]
        }
        
        logger.info(f"Creating Devin session for repo: {request.repository_url}")
        logger.info(f"Service User Token (first 10 chars): {self.service_user_token[:10]}...")
        logger.info(f"Org ID: org-{self.org_id}")
        logger.info(f"Request URL: {self.base_url}/org-{self.org_id}/sessions")
        
        response = httpx.post(
            f"{self.base_url}/org-{self.org_id}/sessions",
            headers=self.headers,
            json=payload,
            timeout=30.0
        )
        
        logger.info(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Response body: {response.text}")
        
        response.raise_for_status()
        
        data = response.json()
        return DevinSessionResponse(
            session_id=data["session_id"],
            session_url=data.get("session_url", ""),
            status=data.get("status", "NEW")
        )

    def get_session_status(self, session_id: str) -> dict:

        logger.info(f"Request URL: {self.base_url}/org-{self.org_id}/sessions/devin-{session_id}")

        response = httpx.get(
            f"{self.base_url}/org-{self.org_id}/sessions/devin-{session_id}",
            headers=self.headers,
            timeout=30.0
        )
        response.raise_for_status()
        
        data = response.json()
        logger.info(f"Session {session_id} status: {data.get('status')}, acu: {data.get('acus_consumed')}")
        return data

    def terminate_session(self, session_id: str) -> bool:

        logger.info(f"Terminating Devin session: {session_id}")
        logger.info(f"Request URL: {self.base_url}/org-{self.org_id}/sessions/devin-{session_id}/terminate")
        
        response = httpx.delete(
            f"{self.base_url}/org-{self.org_id}/sessions/devin-{session_id}/terminate",
            headers=self.headers,
            timeout=30.0
        )
        
        logger.info(f"Terminate response status: {response.status_code}")
        
        # 404 means session already terminated or doesn't exist - treat as success
        if response.status_code in [200, 204, 404]:
            if response.status_code == 404:
                logger.info(f"Session {session_id} not found - likely already terminated")
            return True
        
        logger.error(f"Failed to terminate session: {response.text}")
        return False

    def _build_prompt(self, request: DevinSessionRequest) -> str:
        return f"""
You are an expert software engineer tasked with remediating a GitHub issue.

Repository: {request.repository_url}
Issue Number: {request.issue_number}
Issue Title: {request.title}
Issue Description: {request.description}

Your task:
1. Analyze the issue and understand what needs to be fixed.
2. Implement the necessary changes to resolve the issue.
3. Write appropriate tests to validate your changes.
4. Create a pull request with your changes.

Considerations:
- Always check if the repository is a fork and handle it appropriately.
- Ensure the pull request is created in the correct repository.
- Consider the issue may not be a replicable issue and you can disconsider it if it's not, explaining why.
- If the issue is not clear or you cannot understand what needs to be fixed, you can ask for clarification.
- You don't have to create a pull request if you cannot understand the issue or if it's not a replicable issue.
- Always use screenshots to provide visual evidence if the fix is related to the UI.

Requirements:
- Follow the repository's existing code style and conventions.
- Ensure all tests pass before creating the PR.
- Write clear commit messages.
- Include a summary of changes in the PR description.

After completing the task, provide:
- Pull request URL (or explanation if not created)
- Summary of changes made
- Any notes about the implementation
"""
