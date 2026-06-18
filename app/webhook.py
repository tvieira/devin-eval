import hmac
import hashlib
import logging
from fastapi import Request, HTTPException
from app.config import config

logger = logging.getLogger(__name__)
from app.models import GitHubIssue, DevinSessionRequest
from app.devin import DevinClient
from app.database import create_session, get_session_by_github_issue, update_session
from app.models import Session, SessionStatus
from datetime import datetime


def verify_webhook_signature(payload: bytes, signature: str) -> bool:
    if not config.GITHUB_WEBHOOK_SECRET:
        return True
    
    expected_signature = hmac.new(
        config.GITHUB_WEBHOOK_SECRET.encode(),
        payload,
        hashlib.sha256
    ).hexdigest()
    
    return hmac.compare_digest(f"sha256={expected_signature}", signature)


async def handle_github_webhook(request: Request) -> dict:
    payload = await request.body()
    signature = request.headers.get("X-Hub-Signature-256", "")
    
    if not verify_webhook_signature(payload, signature):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Handle empty body (e.g., ping events)
    if not payload:
        return {"status": "ignored", "reason": "Empty payload"}
    
    try:
        data = await request.json()
    except Exception as e:
        logger.error(f"Failed to parse JSON: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON")
    
    event_type = request.headers.get("X-GitHub-Event", "")
    
    if event_type != "issues":
        return {"status": "ignored", "reason": "Not an issues event"}
    
    action = data.get("action", "")
    
    # Handle issue closure - terminate associated Devin session
    if action == "closed":
        issue_data = data.get("issue", {})
        issue_number = issue_data["number"]
        
        logger.info(f"Issue #{issue_number} closed, checking for active Devin session")
        
        session = get_session_by_github_issue(issue_number)
        
        if session and session.status == SessionStatus.RUNNING:
            logger.info(f"Found running session {session.devin_session_id} for issue #{issue_number}, terminating")
            
            devin_client = DevinClient()
            devin_client.terminate_session(session.devin_session_id)
            
            session.status = SessionStatus.COMPLETED
            session.updated_at = datetime.utcnow()
            session.completed_at = datetime.utcnow()
            
            update_session(session)
            
            logger.info(f"Session {session.devin_session_id} terminated and marked as completed")
            
            return {"status": "terminated", "session_id": session.devin_session_id}
        else:
            logger.info(f"No running session found for issue #{issue_number}")
            return {"status": "ignored", "reason": "No running session for this issue"}
    
    if action != "opened":
        return {"status": "ignored", "reason": "Not an opened event"}
    
    issue_data = data.get("issue", {})
    repository_data = data.get("repository", {})
    
    issue = GitHubIssue(
        number=issue_data["number"],
        title=issue_data["title"],
        description=issue_data.get("body", ""),
        repository_url=repository_data["html_url"]
    )
    
    devin_request = DevinSessionRequest(
        repository_url=issue.repository_url,
        issue_number=issue.number,
        title=issue.title,
        description=issue.description
    )
    
    devin_client = DevinClient()
    devin_response = devin_client.create_session(devin_request)
    
    session = Session(
        github_issue=issue.number,
        devin_session_id=devin_response.session_id,
        status=SessionStatus.RUNNING,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    
    create_session(session)
    
    return {
        "status": "created",
        "session_id": devin_response.session_id,
        "session_url": devin_response.session_url
    }
