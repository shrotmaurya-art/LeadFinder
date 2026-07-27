"""Ensure the Ollama server is running before generation calls."""

import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import config
from utils.logger import get_logger

LOG_DIR = Path(__file__).resolve().parent.parent / "data" / "logs"
logger = get_logger("ollama_manager")


def _is_ollama_reachable() -> bool:
    """Return True if Ollama responds to an HTTP GET on its root endpoint."""
    try:
        req = urllib.request.Request(config.OLLAMA_URL, method="GET")
        with urllib.request.urlopen(req, timeout=5) as resp:
            resp.read()
        return True
    except (urllib.error.URLError, OSError):
        return False


def _start_ollama() -> subprocess.Popen | None:
    """Launch 'ollama serve' as a detached background process.

    Returns the Popen handle on success, or None if the binary is missing.
    """
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    log_path = LOG_DIR / "ollama_serve.log"

    if sys.platform == "win32":
        log_fh = open(log_path, "a", encoding="utf-8")
        creation = subprocess.CREATE_NO_WINDOW  # type: ignore[attr-defined]
        proc = subprocess.Popen(
            ["ollama", "serve"],
            stdout=log_fh,
            stderr=log_fh,
            creationflags=creation,
        )
    else:
        log_fh = open(log_path, "a", encoding="utf-8")
        proc = subprocess.Popen(
            ["ollama", "serve"],
            stdout=log_fh,
            stderr=log_fh,
            start_new_session=True,
        )
    return proc


def ensure_ollama_running(timeout_seconds: int = config.OLLAMA_STARTUP_TIMEOUT) -> bool:
    """Make sure Ollama is reachable, starting it if necessary.

    Returns True if Ollama is (or becomes) reachable within *timeout_seconds*,
    False otherwise.  Never raises.
    """
    try:
        # 1. Already running?
        if _is_ollama_reachable():
            logger.info("Ollama is already running at %s", config.OLLAMA_URL)
            return True

        # 2. Start it
        logger.info("Ollama not reachable – starting 'ollama serve' ...")
        proc = _start_ollama()
        if proc is None:
            logger.error(
                "The 'ollama' binary was not found on PATH. "
                "Install Ollama from https://ollama.com and ensure it is on your PATH."
            )
            return False

        # 3. Poll until reachable or timeout
        deadline = time.monotonic() + timeout_seconds
        while time.monotonic() < deadline:
            time.sleep(1)
            if _is_ollama_reachable():
                logger.info("Ollama is now reachable after auto-start.")
                return True

        logger.error(
            "Ollama was started but did not become reachable within %d seconds.",
            timeout_seconds,
        )
        return False

    except FileNotFoundError:
        logger.error(
            "The 'ollama' binary was not found on PATH. "
            "Install Ollama from https://ollama.com and ensure it is on your PATH."
        )
        return False
