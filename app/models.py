from enum import Enum
from datetime import datetime
from pydantic import BaseModel


class SessionStatus(str, Enum):
    NEW = "NEW"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Session(BaseModel):
    id: int | None = None
    github_issue: int
    devin_session_id: str
    status: SessionStatus
    created_at: datetime
    updated_at: datetime
    completed_at: datetime | None = None
    pr_url: str | None = None
    error_message: str | None = None
    acu: float | None = None


class GitHubIssue(BaseModel):
    number: int
    title: str
    description: str
    repository_url: str


class DevinSessionRequest(BaseModel):
    repository_url: str
    issue_number: int
    title: str
    description: str


class DevinSessionResponse(BaseModel):
    session_id: str
    session_url: str
    status: str
