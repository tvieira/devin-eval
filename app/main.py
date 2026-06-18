import asyncio
import logging
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse

from app.config import config
from app.database import init_db, get_running_sessions, update_session, get_session_stats, get_all_sessions
from app.devin import DevinClient
from app.github import GitHubClient
from app.models import SessionStatus
from app.webhook import handle_github_webhook

logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Devin Automation Service")

app.mount("/static", StaticFiles(directory="static"), name="static")

devin_client = DevinClient()
github_client = GitHubClient()


@app.on_event("startup")
async def startup_event():
    logger.info("Starting Devin Automation Service")
    init_db()
    asyncio.create_task(poll_sessions())


@app.post("/github/webhook")
async def github_webhook(request: Request):
    logger.info("Webhook received")
    result = await handle_github_webhook(request)
    logger.info(f"Webhook processed: {result}")
    return result


@app.get("/status")
async def status():
    stats = get_session_stats()
    return {
        "status": "healthy",
        **stats
    }


@app.get("/dashboard")
async def dashboard():
    stats = get_session_stats()
    all_sessions = get_all_sessions()
    
    completed_count = stats["completed"]
    failed_count = stats["failed"]
    total_finished = completed_count + failed_count
    success_rate = (completed_count / total_finished * 100) if total_finished > 0 else 0
    
    recent_activity = []
    for session in all_sessions[:10]:
        recent_activity.append({
            "issue": session.github_issue,
            "status": session.status
        })
    
    total_time = 0
    time_count = 0
    total_acu = 0
    acu_count = 0
    for session in all_sessions:
        if session.completed_at and session.created_at:
            duration = (session.completed_at - session.created_at).total_seconds() / 60
            total_time += duration
            time_count += 1
        if session.acu:
            total_acu += session.acu
            acu_count += 1
    
    avg_fix_time = (total_time / time_count) if time_count > 0 else 0
    avg_acu = (total_acu / acu_count) if acu_count > 0 else 0
    
    return {
        "active_sessions": stats["active"],
        "completed_sessions": stats["completed"],
        "failed_sessions": stats["failed"],
        "prs_created": stats["prs_created"],
        "success_rate": round(success_rate, 1),
        "average_fix_time_minutes": round(avg_fix_time, 1),
        "average_acu": round(avg_acu, 2),
        "recent_activity": recent_activity
    }


async def poll_sessions():
    logger.info("Starting background polling task")
    while True:
        try:
            await check_active_sessions()
        except Exception as e:
            logger.error(f"Error during polling: {e}")
        
        await asyncio.sleep(config.POLL_INTERVAL)


async def check_active_sessions():
    running_sessions = get_running_sessions()
    
    if not running_sessions:
        return
    
    logger.info(f"Polling {len(running_sessions)} running session(s)")
    
    for session in running_sessions:
        try:
            status_data = devin_client.get_session_status(session.devin_session_id)
            status = status_data.get("status", "RUNNING")
            
            if status == "COMPLETED":
                logger.info(f"Session {session.devin_session_id} completed")
                session.status = SessionStatus.COMPLETED
                session.updated_at = datetime.utcnow()
                session.completed_at = datetime.utcnow()
                session.pr_url = status_data.get("pr_url")
                session.acu = status_data.get("acus_consumed")
                
                update_session(session)
                
                # Update GitHub
                repo_url_parts = session.pr_url.split("/") if session.pr_url else []
                if len(repo_url_parts) >= 4:
                    repo_owner = repo_url_parts[-4]
                    repo_name = repo_url_parts[-3]
                    github_client.post_completion_comment(
                        repo_owner,
                        repo_name,
                        session.github_issue,
                        status_data.get("session_url", ""),
                        session.pr_url,
                        status_data.get("summary", "No summary provided")
                    )
                    logger.info(f"Updated GitHub issue #{session.github_issue}")
                
            elif status == "FAILED":
                logger.info(f"Session {session.devin_session_id} failed")
                session.status = SessionStatus.FAILED
                session.updated_at = datetime.utcnow()
                session.error_message = status_data.get("error", "Unknown error")
                
                update_session(session)
                
            else:
                session.updated_at = datetime.utcnow()
                update_session(session)
                
        except Exception as e:
            logger.error(f"Error checking session {session.devin_session_id}: {e}")
