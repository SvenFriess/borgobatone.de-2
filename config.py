import os
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class Config:
    SIGNAL_NUMBER = os.getenv("SIGNAL_NUMBER", "").strip()
    SIGNAL_GROUP_ID = os.getenv("SIGNAL_GROUP_ID", "").strip()
    BOT_TRIGGER = os.getenv("BOT_TRIGGER", "!Bot").strip()

    RECV_TIMEOUT = int(os.getenv("RECV_TIMEOUT", "300"))
    LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "25"))
    SEND_RETRY = int(os.getenv("SEND_RETRY", "3"))
    SEND_RETRY_WAIT = float(os.getenv("SEND_RETRY_WAIT", "1.0"))

    USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
    LLM_MODEL = os.getenv("LLM_MODEL", "mistral:instruct").strip()
    LLM_MAX_TOKENS = int(os.getenv("LLM_MAX_TOKENS", "300"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
    LOG_FILE = os.getenv("LOG_FILE", "logs/borgo-bot.log")

    # 👉 Hier wichtig: FIXED_FILE wird aus der .env gelesen
    FIXED_FILE = str(Path(os.getenv("FIXED_FILE", "FIXED_RESPONSES.txt")).expanduser().resolve())

    DAEMON_MODE = os.getenv("DAEMON_MODE", "false").lower() == "true"

    @staticmethod
    def validate():
        missing = []
        if not Config.SIGNAL_NUMBER:
            missing.append("SIGNAL_NUMBER")
        if not Config.SIGNAL_GROUP_ID:
            missing.append("SIGNAL_GROUP_ID")
        if missing:
            raise ValueError(f"Missing required env vars: {', '.join(missing)}")