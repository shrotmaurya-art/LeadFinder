import os
from dotenv import load_dotenv

load_dotenv()

def _bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in ("true", "1", "yes")

CITY: str = os.getenv("CITY", "")
CATEGORIES: list[str] = [c.strip() for c in os.getenv("CATEGORIES", "").split(",") if c.strip()]
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
COOLDOWN_DAYS: int = int(os.getenv("COOLDOWN_DAYS", "15"))
MAX_FOLLOW_UPS: int = int(os.getenv("MAX_FOLLOW_UPS", "2"))
EMAIL_DAILY_CAP: int = int(os.getenv("EMAIL_DAILY_CAP", "30"))
WHATSAPP_DAILY_CAP: int = int(os.getenv("WHATSAPP_DAILY_CAP", "30"))
LEAD_SCORE_THRESHOLD: int = int(os.getenv("LEAD_SCORE_THRESHOLD", "40"))
APP_TIMEZONE: str = os.getenv("APP_TIMEZONE", "Asia/Kolkata")
DATA_SOURCE: str = os.getenv("DATA_SOURCE", "playwright")
GOOGLE_PLACES_API_KEY: str = os.getenv("GOOGLE_PLACES_API_KEY", "")
INCLUDE_RATINGS_VIA_API: bool = _bool(os.getenv("INCLUDE_RATINGS_VIA_API", "false"))
