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

# Freelancer profile (used in outreach messages)
FREELANCER_NAME: str = os.getenv("FREELANCER_NAME", "")
FREELANCER_PITCH: str = os.getenv(
    "FREELANCER_PITCH",
    "independent freelance web developer — modern, fast, affordable websites",
)
STARTING_PRICE: str = os.getenv("STARTING_PRICE", "Rs. 3,999")
PORTFOLIO_URL: str = os.getenv("PORTFOLIO_URL", "")

# Notification settings
NOTIFY_EMAIL: str = os.getenv("NOTIFY_EMAIL", "")
SMTP_HOST: str = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT: int = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER: str = os.getenv("SMTP_USER", "")
SMTP_PASSWORD: str = os.getenv("SMTP_PASSWORD", "")
ENABLE_EMAIL_NOTIFY: bool = _bool(os.getenv("ENABLE_EMAIL_NOTIFY", "true"))
ENABLE_DESKTOP_NOTIFY: bool = _bool(os.getenv("ENABLE_DESKTOP_NOTIFY", "true"))
