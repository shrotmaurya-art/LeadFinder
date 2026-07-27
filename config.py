import os
from dotenv import load_dotenv

load_dotenv()

def _bool(value: str | None) -> bool:
    if value is None:
        return False
    return value.strip().lower() in ("true", "1", "yes")

CITIES: list[str] = [c.strip() for c in os.getenv("CITIES", "").split(",") if c.strip()]
CATEGORIES: list[str] = [c.strip() for c in os.getenv("CATEGORIES", "").split(",") if c.strip()]
OLLAMA_MODEL: str = os.getenv("OLLAMA_MODEL", "llama3.1:8b")
COOLDOWN_DAYS: int = int(os.getenv("COOLDOWN_DAYS", "15"))
MAX_FOLLOW_UPS: int = int(os.getenv("MAX_FOLLOW_UPS", "2"))
EMAIL_DAILY_CAP: int = int(os.getenv("EMAIL_DAILY_CAP", "30"))
EMAIL_LINK_STYLE: str = os.getenv("EMAIL_LINK_STYLE", "mailto")
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

# Scout / Playwright settings
SEARCH_DELAY_MIN: float = float(os.getenv("SEARCH_DELAY_MIN", "2.0"))
SEARCH_DELAY_MAX: float = float(os.getenv("SEARCH_DELAY_MAX", "5.0"))
PAGE_LOAD_TIMEOUT_MS: int = int(os.getenv("PAGE_LOAD_TIMEOUT_MS", "10000"))
MAX_SCROLL_ATTEMPTS: int = int(os.getenv("MAX_SCROLL_ATTEMPTS", "3"))
SCROLL_TARGET_RESULTS: int = int(os.getenv("SCROLL_TARGET_RESULTS", "20"))

# Google Places API settings
PLACES_CACHE_TTL_SECONDS: int = int(os.getenv("PLACES_CACHE_TTL_SECONDS", "86400"))
PLACES_API_TIMEOUT: int = int(os.getenv("PLACES_API_TIMEOUT", "30"))

# Website extraction settings
CONTENT_FETCH_TIMEOUT: int = int(os.getenv("CONTENT_FETCH_TIMEOUT", "8"))

# Deduplication settings
SOFT_MATCH_THRESHOLD: int = int(os.getenv("SOFT_MATCH_THRESHOLD", "90"))

# Outreach sender settings
COPY_FALLBACK_LIMIT: int = int(os.getenv("COPY_FALLBACK_LIMIT", "1800"))

# Ollama settings
OLLAMA_URL: str = os.getenv("OLLAMA_URL", "http://localhost:11434")
OLLAMA_TIMEOUT: int = int(os.getenv("OLLAMA_TIMEOUT", "15"))
OLLAMA_RETRIES: int = int(os.getenv("OLLAMA_RETRIES", "2"))
OLLAMA_STARTUP_TIMEOUT: int = int(os.getenv("OLLAMA_STARTUP_TIMEOUT", "20"))

# LLM generation token limits
EMAIL_MAX_TOKENS: int = int(os.getenv("EMAIL_MAX_TOKENS", "250"))
SUBJECT_MAX_TOKENS: int = int(os.getenv("SUBJECT_MAX_TOKENS", "30"))
WHATSAPP_MAX_TOKENS: int = int(os.getenv("WHATSAPP_MAX_TOKENS", "120"))
WHATSAPP_CHAR_LIMIT: int = int(os.getenv("WHATSAPP_CHAR_LIMIT", "400"))

# Database settings
SQLITE_BUSY_TIMEOUT_MS: int = int(os.getenv("SQLITE_BUSY_TIMEOUT_MS", "5000"))

# Analyzer / scoring settings
REVIEW_COUNT_BAND: int = int(os.getenv("REVIEW_COUNT_BAND", "20"))
RATING_THRESHOLD: float = float(os.getenv("RATING_THRESHOLD", "4.0"))

# Dashboard settings
STREAMLIT_URL: str = os.getenv("STREAMLIT_URL", "http://localhost:8501")
ENABLE_DASHBOARD_AUTO_SCOUT: bool = _bool(os.getenv("ENABLE_DASHBOARD_AUTO_SCOUT", "true"))
