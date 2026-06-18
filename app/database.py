import sqlite3
from datetime import datetime
from typing import List, Optional
from contextlib import contextmanager
from app.config import config
from app.models import Session, SessionStatus


@contextmanager
def get_db_connection():
    conn = sqlite3.connect(config.DATABASE_URL.replace("sqlite:///", ""))
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()


def init_db():
    with get_db_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                github_issue INTEGER NOT NULL,
                devin_session_id TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                completed_at TEXT,
                pr_url TEXT,
                error_message TEXT,
                acu REAL
            )
        """)
        
        # Add acu column if it doesn't exist (for existing databases)
        try:
            conn.execute("ALTER TABLE sessions ADD COLUMN acu REAL")
            conn.commit()
        except Exception as e:
            # Column likely already exists
            pass


def create_session(session: Session) -> Session:
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO sessions (github_issue, devin_session_id, status, created_at, updated_at, acu)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (session.github_issue, session.devin_session_id, session.status, session.created_at.isoformat(), session.updated_at.isoformat(), session.acu)
        )
        conn.commit()
        session.id = cursor.lastrowid
        return session


def get_session_by_id(session_id: int) -> Optional[Session]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE id = ?", (session_id,)).fetchone()
        if row:
            return _row_to_session(row)
        return None


def get_session_by_devin_id(devin_session_id: str) -> Optional[Session]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE devin_session_id = ?", (devin_session_id,)).fetchone()
        if row:
            return _row_to_session(row)
        return None


def get_session_by_github_issue(github_issue: int) -> Optional[Session]:
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM sessions WHERE github_issue = ? ORDER BY created_at DESC LIMIT 1", (github_issue,)).fetchone()
        if row:
            return _row_to_session(row)
        return None


def get_running_sessions() -> List[Session]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM sessions WHERE status = ?", (SessionStatus.RUNNING,)).fetchall()
        return [_row_to_session(row) for row in rows]


def update_session(session: Session) -> Session:
    with get_db_connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET status = ?, updated_at = ?, completed_at = ?, pr_url = ?, error_message = ?, acu = ?
            WHERE id = ?
            """,
            (
                session.status,
                session.updated_at.isoformat(),
                session.completed_at.isoformat() if session.completed_at else None,
                session.pr_url,
                session.error_message,
                session.acu,
                session.id
            )
        )
        conn.commit()
        return session


def get_all_sessions() -> List[Session]:
    with get_db_connection() as conn:
        rows = conn.execute("SELECT * FROM sessions ORDER BY created_at DESC").fetchall()
        return [_row_to_session(row) for row in rows]


def get_session_stats() -> dict:
    with get_db_connection() as conn:
        stats = conn.execute("""
            SELECT 
                COUNT(CASE WHEN status = ? THEN 1 END) as active,
                COUNT(CASE WHEN status = ? THEN 1 END) as completed,
                COUNT(CASE WHEN status = ? THEN 1 END) as failed,
                COUNT(CASE WHEN pr_url IS NOT NULL THEN 1 END) as prs_created
            FROM sessions
        """, (SessionStatus.RUNNING, SessionStatus.COMPLETED, SessionStatus.FAILED)).fetchone()
        
        return {
            "active": stats["active"] or 0,
            "completed": stats["completed"] or 0,
            "failed": stats["failed"] or 0,
            "prs_created": stats["prs_created"] or 0
        }


def _row_to_session(row: sqlite3.Row) -> Session:
    return Session(
        id=row["id"],
        github_issue=row["github_issue"],
        devin_session_id=row["devin_session_id"],
        status=row["status"],
        created_at=datetime.fromisoformat(row["created_at"]),
        updated_at=datetime.fromisoformat(row["updated_at"]),
        completed_at=datetime.fromisoformat(row["completed_at"]) if row["completed_at"] else None,
        pr_url=row["pr_url"],
        error_message=row["error_message"],
        acu=row["acu"]
    )
