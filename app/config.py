import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    DEVIN_SERVICE_USER_TOKEN = os.getenv("DEVIN_SERVICE_USER_TOKEN")
    DEVIN_ORG_ID = os.getenv("DEVIN_ORG_ID")
    GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
    GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./devin_automation.db")
    POLL_INTERVAL = int(os.getenv("POLL_INTERVAL", "30"))


config = Config()
